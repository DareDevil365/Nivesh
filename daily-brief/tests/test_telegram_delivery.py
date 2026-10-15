"""Offline checks for private Telegram pairing, delivery and fail-closed claims."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from services import news_bot, news_digest
from services import telegram_delivery as tg
from tests.test_news_bot import fixture

TOKEN = "123456:" + "x" * 35


def setup_module():
    path = Path(__file__).resolve().parents[1] / "scripts/setup_telegram.py"
    spec = importlib.util.spec_from_file_location("telegram_setup_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TelegramTests(unittest.TestCase):
    def setUp(self):
        self.config = tg.TelegramConfig(TOKEN, "7654321")
        self.digest = news_bot.summarise(fixture()[0], use_ai=False)

    def receipt(self, **changes):
        return {
            "message_id": 42,
            "chat": {"id": 7654321, "type": "private"},
            **changes,
        }

    def test_config_rejects_invalid_tokens_and_nonprivate_destinations(self):
        for token, chat in (
            ("", "7654321"),
            (TOKEN + "/sendMessage", "7654321"),
            (TOKEN, "-1001234"),
            (TOKEN, "@somechannel"),
            (TOKEN, "1\n2"),
        ):
            with patch.dict(
                "os.environ",
                {"NEWS_TELEGRAM_BOT_TOKEN": token, "NEWS_TELEGRAM_CHAT_ID": chat},
                clear=True,
            ):
                with self.assertRaises(news_bot.BotError):
                    tg.TelegramConfig.load()
        with patch.dict("os.environ", {"NEWS_TELEGRAM_BOT_TOKEN": TOKEN}, clear=True):
            self.assertEqual(tg.TelegramConfig.load(require_chat=False).token, TOKEN)
            with self.assertRaises(news_bot.BotError):
                tg.TelegramConfig.load()

    def test_private_credentials_not_in_repr_or_delivery_id(self):
        identifier = self.config.delivery_id("2026-10-15")
        self.assertNotIn(TOKEN, repr(self.config))
        self.assertNotIn(self.config.chat_id, repr(self.config))
        self.assertNotIn(self.config.chat_id, identifier)
        self.assertNotIn(TOKEN, identifier)
        rotated = tg.TelegramConfig("123456:" + "y" * 35, self.config.chat_id)
        self.assertEqual(identifier, rotated.delivery_id("2026-10-15"))
        self.assertNotEqual(identifier, self.config.delivery_id("2026-10-16"))
        self.assertNotEqual(
            identifier, tg.TelegramConfig(TOKEN, "7654322").delivery_id("2026-10-15")
        )

    def test_messages_preserve_unicode_full_text_html_escaping_and_clickable_links(self):
        section = self.digest["sections"][0]
        bullet = section["bullets"][0]
        text = "😀" * 650
        bullet["text"] = text
        bullet["why_it_matters"] = "Rates < inflation & risk > return"
        self.digest["sections"] = [section] * 6
        messages = tg.render_messages(self.digest)
        result = "\n".join(messages)
        self.assertGreater(len(messages), 1)
        self.assertEqual(result.count(text), 6)
        self.assertIn("Rates &lt; inflation &amp; risk &gt; return", result)
        self.assertIn('<a href="https://example.com/story">', result)
        self.assertIn("headline fallback", result)
        self.assertIn("AI interpretation is unverified", result)
        for index, message in enumerate(messages, 1):
            self.assertLessEqual(len(message.encode("utf-16-le")) // 2, 4096)
            self.assertIn(f"{index}/{len(messages)}", message)
            self.assertEqual(message.count('<a href="'), message.count("</a>"))

    def test_unsafe_links_and_oversized_blocks_fail_before_claim_or_send(self):
        for url in ("javascript:alert(1)", "https://example.com/" + "x" * 4000):
            self.digest["sections"][0]["bullets"][0]["sources"][0]["url"] = url
            with patch.object(tg, "api") as api, patch.object(news_bot, "LocalLedger") as factory:
                factory.return_value.get.return_value = None
                with self.assertRaises(news_bot.BotError):
                    tg.deliver(self.digest, self.config, factory.return_value)
                factory.return_value.reserve.assert_not_called()
                api.assert_not_called()

    def test_transport_https_exact_chat_no_redirect_or_retry(self):
        response = httpx.Response(200, json={"ok": True, "result": self.receipt()})
        with patch.object(tg.httpx, "Client") as factory:
            client = factory.return_value.__enter__.return_value
            client.post.return_value = response
            result = tg.api(
                self.config,
                "sendMessage",
                data={"chat_id": self.config.chat_id},
            )
        self.assertEqual(result["message_id"], 42)
        self.assertEqual(factory.call_args.kwargs["follow_redirects"], False)
        self.assertEqual(factory.call_args.kwargs["trust_env"], False)
        self.assertEqual(client.post.call_count, 1)
        self.assertTrue(client.post.call_args.args[0].startswith("https://api.telegram.org/"))
        self.assertEqual(client.post.call_args.kwargs["data"], {"chat_id": self.config.chat_id})

    def test_errors_do_not_expose_token_url_provider_body_or_retry(self):
        url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
        outcomes = [
            httpx.ConnectError(url),
            httpx.Response(403, json={"description": TOKEN}),
            httpx.Response(200, text=TOKEN),
            httpx.Response(200, json={"ok": False, "description": TOKEN}),
        ]
        for outcome in outcomes:
            with patch.object(tg.httpx, "Client") as factory:
                post = factory.return_value.__enter__.return_value.post
                if isinstance(outcome, Exception):
                    post.side_effect = outcome
                else:
                    post.return_value = outcome
                with self.assertRaises(news_bot.BotError) as caught:
                    tg.api(self.config, "sendMessage")
                self.assertNotIn(TOKEN, str(caught.exception))
                self.assertEqual(post.call_count, 1)

    def test_check_rejects_wrong_chat_or_bot_identity(self):
        me = {"id": 123456, "is_bot": True}
        for result in (None, {"id": 99, "type": "private"}, {"id": 7654321, "type": "group"}):
            with (
                patch.object(tg, "api", side_effect=[me, result]),
                self.assertRaises(news_bot.BotError),
            ):
                tg.check(self.config)
        with (
            patch.object(tg, "api", return_value={"id": 123457, "is_bot": True}) as api,
            self.assertRaises(news_bot.BotError),
        ):
            tg.check(self.config)
        self.assertEqual(api.call_count, 1)

    def test_delivery_claims_first_sends_full_sources_and_skips_repeat(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(tg, "api") as api,
        ):
            ledger = news_bot.LocalLedger()
            key = hashlib.sha256(
                self.config.delivery_id(self.digest["date_ist"]).encode()
            ).hexdigest()[:32]

            def send(config, method, **kwargs):
                self.assertEqual(ledger.get(key)["status"], "pending")
                self.assertEqual(method, "sendMessage")
                self.assertEqual(kwargs["data"]["chat_id"], self.config.chat_id)
                self.assertNotIn("files", kwargs)
                self.assertEqual(kwargs["data"]["parse_mode"], "HTML")
                self.assertIn('href="https://example.com/story"', kwargs["data"]["text"])
                self.assertEqual(
                    json.loads(kwargs["data"]["link_preview_options"]), {"is_disabled": True}
                )
                return self.receipt()

            api.side_effect = send
            self.assertEqual(tg.deliver(self.digest, self.config, ledger), "telegram_accepted")
            self.assertEqual(tg.deliver(self.digest, self.config, ledger), "already_accepted")
            self.assertEqual(api.call_count, 1)
            record = json.dumps(ledger.get(key))
            self.assertNotIn(self.config.chat_id, record)
            self.assertNotIn(TOKEN, record)

    def test_partial_multipart_send_records_progress_and_never_replays(self):
        section = self.digest["sections"][0]
        section["bullets"][0]["text"] = "😀" * 650
        self.digest["sections"] = [section] * 6
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(tg.time, "sleep"),
            patch.object(
                tg, "api", side_effect=[self.receipt(), news_bot.BotError("uncertain")]
            ) as api,
        ):
            ledger = news_bot.LocalLedger()
            key = hashlib.sha256(
                self.config.delivery_id(self.digest["date_ist"]).encode()
            ).hexdigest()[:32]
            with self.assertRaises(news_bot.BotError):
                tg.deliver(self.digest, self.config, ledger)
            self.assertEqual(ledger.get(key)["confirmed_parts"], 1)
            self.assertEqual(ledger.get(key)["status"], "pending")
            with self.assertRaises(news_bot.BotError):
                tg.deliver(self.digest, self.config, ledger)
            self.assertEqual(api.call_count, 2)

    def test_complete_multipart_send_marks_accepted_only_after_last_part(self):
        section = self.digest["sections"][0]
        section["bullets"][0]["text"] = "😀" * 650
        self.digest["sections"] = [section] * 6
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(tg.time, "sleep"),
            patch.object(tg, "api", return_value=self.receipt()) as api,
        ):
            ledger = news_bot.LocalLedger()
            self.assertEqual(tg.deliver(self.digest, self.config, ledger), "telegram_accepted")
            key = hashlib.sha256(
                self.config.delivery_id(self.digest["date_ist"]).encode()
            ).hexdigest()[:32]
            self.assertEqual(ledger.get(key)["confirmed_parts"], ledger.get(key)["total_parts"])
            self.assertGreater(api.call_count, 1)
            self.assertEqual(tg.deliver(self.digest, self.config, ledger), "already_accepted")

    def test_uncertain_delivery_or_wrong_receipt_keeps_claim_without_resend(self):
        for outcome in (
            news_bot.BotError("timeout"),
            self.receipt(chat={"id": 99, "type": "private"}),
            self.receipt(message_id=0),
        ):
            with (
                tempfile.TemporaryDirectory() as folder,
                patch.object(news_digest, "DIGEST_DIR", Path(folder)),
                patch.object(tg, "api") as api,
            ):
                ledger = news_bot.LocalLedger()
                if isinstance(outcome, Exception):
                    api.side_effect = outcome
                else:
                    api.return_value = outcome
                with self.assertRaises(news_bot.BotError):
                    tg.deliver(self.digest, self.config, ledger)
                with self.assertRaises(news_bot.BotError):
                    tg.deliver(self.digest, self.config, ledger)
                self.assertEqual(api.call_count, 1)

    def test_pairing_requires_nonce_recent_private_human_message_and_unique_chat(self):
        pair = setup_module().pairing_chat
        code = "a" * 24
        message = {
            "text": "/start " + code,
            "date": 9990,
            "chat": {"type": "private", "id": 7654321},
            "from": {"id": 7654321, "is_bot": False},
        }
        self.assertEqual(pair([{"message": message}], code, 10000), "7654321")
        invalid = [
            {**message, "text": "/start wrong"},
            {**message, "date": 1},
            {**message, "chat": {"type": "group", "id": -1}},
            {**message, "from": {"id": 7654321, "is_bot": True}},
            {**message, "from": {"id": 123}},
        ]
        for candidate in invalid:
            with self.assertRaises(news_bot.BotError):
                pair([{"message": candidate}], code, 10000)
        second = {**message, "chat": {"type": "private", "id": 7654322}, "from": {"id": 7654322}}
        with self.assertRaises(news_bot.BotError):
            pair([{"message": message}, {"message": second}], code, 10000)


if __name__ == "__main__":
    unittest.main()
