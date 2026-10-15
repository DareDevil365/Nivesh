"""Standalone tests also run in the small hosted deployment bundle."""

import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from services import news_bot as bot
from services import news_digest


def fixture():
    source = {
        "id": "source-one",
        "title": "US inflation falls to 3 percent",
        "url": "https://example.com/story",
        "publisher": "Example",
        "published_at": "2026-10-14T00:30:00+00:00",
        "read_status": "headline_only",
        "categories": ["us"],
        "evidence_text": "",
    }
    pack = {
        "items": [source],
        "date_ist": "2026-10-14",
        "generated_at": "2026-10-14T00:30:00Z",
        "coverage": {"headlines": 1, "article_excerpts": 0, "feed_excerpts": 0, "headline_only": 1},
        "feeds": [],
        "limitations": "Fixture",
    }
    section = {
        "category": "us",
        "bullets": [
            {
                "text": "A report says US inflation has fallen to 3 percent.",
                "why_it_matters": "Check the original release before drawing a rate conclusion.",
                "support": [{"source_id": source["id"], "quote": source["title"]}],
            }
        ],
    }
    return pack, section


def provider(section):
    return SimpleNamespace(
        status_code=200,
        json=lambda: {
            "candidates": [
                {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(section)}]}}
            ]
        },
    )


class NewsBotTests(unittest.TestCase):
    def test_valid_ai_section_without_private_mail_data(self):
        pack, section = fixture()
        with (
            patch.object(bot.gemini_rotator, "get_status", return_value={"active_keys": 1}),
            patch.object(
                bot.gemini_rotator, "post", return_value=(provider(section), "fake-key")
            ) as post,
            patch.object(bot.gemini_rotator, "report_success"),
        ):
            self.assertEqual(bot.generate_section(pack, "us", pack["items"]), section)
            self.assertNotIn("NEWS_SMTP_PASSWORD", str(post.call_args))
            self.assertNotIn("NEWS_EMAIL_TO", str(post.call_args))

    def test_invalid_ai_numbers_receive_one_repair_then_fallback(self):
        pack, section = fixture()
        section["bullets"][0]["text"] = "A report says inflation has fallen to 9 percent."
        with (
            patch.object(bot.gemini_rotator, "get_status", return_value={"active_keys": 1}),
            patch.object(
                bot.gemini_rotator, "post", return_value=(provider(section), "fake-key")
            ) as post,
            patch.object(bot.gemini_rotator, "report_success"),
        ):
            self.assertIsNone(bot.generate_section(pack, "us", pack["items"]))
            self.assertEqual(post.call_count, 2)

    def test_headline_fallback_is_explicit_and_validated(self):
        pack, _ = fixture()
        result = bot.summarise(pack, use_ai=False)
        self.assertEqual(result["summary_status"], "headline_fallback")
        self.assertIn("Reported headline:", result["sections"][0]["bullets"][0]["text"])
        self.assertIn("headline fallback", news_digest.email_text(result))

    def test_partial_generation_does_not_hide_fallback(self):
        pack, section = fixture()
        second = {
            **pack["items"][0],
            "id": "second",
            "title": "India reports annual inflation release",
            "categories": ["india"],
        }
        pack["items"].append(second)
        with patch.object(
            bot,
            "generate_section",
            side_effect=lambda pack, category, items: section if category == "us" else None,
        ):
            result = bot.summarise(pack)
        self.assertEqual(result["summary_status"], "partial_ai")
        self.assertEqual(result["summary_modes"]["india"], "headline_fallback")

    def test_empty_pack_never_invents_a_quiet_market(self):
        pack, _ = fixture()
        pack["items"] = []
        with self.assertRaises(bot.BotError):
            bot.summarise(pack)

    def test_mail_config_rejects_injection_and_missing_password(self):
        for recipient in (
            "a@example.com\r\nBcc: victim@example.com",
            "a@example.com,b@example.com",
            "",
        ):
            with (
                patch.dict(
                    "os.environ",
                    {
                        "NEWS_SMTP_USER": "sender@example.com",
                        "NEWS_SMTP_PASSWORD": "fake-app-password",
                        "NEWS_EMAIL_TO": recipient,
                    },
                    clear=True,
                ),
                self.assertRaises(bot.BotError),
            ):
                bot.MailConfig.load()
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(bot.BotError):
            bot.MailConfig.load()

    def test_password_not_in_repr_and_ids_are_stable_private_and_day_specific(self):
        config = bot.MailConfig("sender@gmail.com", "private-password", "reader@example.com")
        self.assertNotIn("private-password", repr(config))
        self.assertNotIn("reader@example.com", config.message_id("2026-10-14"))
        self.assertEqual(config.message_id("2026-10-14"), config.message_id("2026-10-14"))
        self.assertNotEqual(config.message_id("2026-10-14"), config.message_id("2026-10-15"))

    def test_smtp_is_plain_text_has_exact_envelope_and_tls(self):
        pack, _ = fixture()
        digest = bot.summarise(pack, use_ai=False)
        config = bot.MailConfig("sender@gmail.com", "private-password", "reader@example.com")
        with patch.object(bot.smtplib, "SMTP_SSL") as smtp:
            client = smtp.return_value
            client.__enter__.return_value = client
            client.send_message.return_value = {}
            bot.send_smtp(config, digest, config.message_id(pack["date_ist"]))
        message = client.send_message.call_args.args[0]
        self.assertEqual(message.get_content_type(), "text/plain")
        self.assertEqual(message["To"], config.recipient)
        self.assertEqual(message["From"], config.user)
        self.assertEqual(client.send_message.call_args.kwargs["to_addrs"], [config.recipient])
        self.assertIn("context", smtp.call_args.kwargs)

    def test_imap_uses_sent_flag_and_narrow_message_id_search(self):
        config = bot.MailConfig("sender@gmail.com", "private-password", "reader@example.com")
        with patch.object(bot.imaplib, "IMAP4_SSL") as imap:
            client = imap.return_value.__enter__.return_value
            client.list.return_value = ("OK", [b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Sent Mail"'])
            client.select.return_value = ("OK", [b"1"])
            client.search.return_value = ("OK", [b"99"])
            self.assertTrue(bot.sent_message_exists(config, config.message_id("2026-10-14")))
            self.assertEqual(client.select.call_args.kwargs, {"readonly": True})
            self.assertEqual(client.search.call_args.args[1:3], ("HEADER", "Message-ID"))

    def test_imap_failure_refuses_send(self):
        config = bot.MailConfig("sender@gmail.com", "private-password", "reader@example.com")
        with (
            patch.object(bot.imaplib, "IMAP4_SSL", side_effect=OSError("not available")),
            self.assertRaises(bot.BotError),
        ):
            bot.sent_message_exists(config, config.message_id("2026-10-14"))

    def test_success_claims_before_sending_and_second_run_skips(self):
        pack, _ = fixture()
        digest = bot.summarise(pack, use_ai=False)
        config = bot.MailConfig("sender@gmail.com", "private-password", "reader@example.com")
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(bot, "sent_message_exists", return_value=False),
            patch.object(bot, "send_smtp") as send,
        ):
            ledger = bot.LocalLedger()

            def assert_reserved(*args):
                key = hashlib.sha256(config.message_id(pack["date_ist"]).encode()).hexdigest()[:32]
                self.assertEqual(ledger.get(key)["status"], "pending")

            send.side_effect = assert_reserved
            self.assertEqual(bot.deliver(digest, config, ledger), "smtp_accepted")
            self.assertEqual(bot.deliver(digest, config, ledger), "already_accepted")
            self.assertEqual(send.call_count, 1)

    def test_ambiguous_smtp_does_not_blindly_resend(self):
        pack, _ = fixture()
        digest = bot.summarise(pack, use_ai=False)
        config = bot.MailConfig("sender@gmail.com", "private-password", "reader@example.com")
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(bot, "sent_message_exists", return_value=False),
            patch.object(bot, "send_smtp", side_effect=bot.BotError("ambiguous")) as send,
        ):
            ledger = bot.LocalLedger()
            with self.assertRaises(bot.BotError):
                bot.deliver(digest, config, ledger)
            with self.assertRaises(bot.BotError):
                bot.deliver(digest, config, ledger)
            self.assertEqual(send.call_count, 1)

    def test_existing_sent_message_records_acceptance_without_new_send(self):
        pack, _ = fixture()
        config = bot.MailConfig("sender@gmail.com", "private-password", "reader@example.com")
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(bot, "sent_message_exists", return_value=True),
            patch.object(bot, "send_smtp") as send,
        ):
            self.assertEqual(
                bot.deliver(bot.summarise(pack, use_ai=False), config, bot.LocalLedger()),
                "already_in_sent",
            )
            send.assert_not_called()

    def test_local_claim_is_exclusive(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
        ):
            ledger = bot.LocalLedger()
            ledger.reserve("key", {"status": "pending"})
            with self.assertRaises(FileExistsError):
                ledger.reserve("key", {"status": "pending"})

    def test_remote_ledger_rejects_failed_writes_and_uses_optimistic_sha(self):
        ledger = bot.GitHubLedger("owner/repo", "fake-token")
        with patch.object(ledger.client, "request", return_value=httpx.Response(404)):
            self.assertIsNone(ledger.get("key"))
            with self.assertRaises(bot.BotError):
                ledger.request("PUT", "/contents/test")
        stored = base64.b64encode(json.dumps({"status": "pending"}).encode()).decode()
        with patch.object(
            ledger.client,
            "request",
            side_effect=[
                httpx.Response(200, json={"sha": "current-sha", "content": stored}),
                httpx.Response(200),
            ],
        ) as request:
            ledger.accepted("key", {"status": "accepted"})
            self.assertEqual(request.call_args.kwargs["json"]["sha"], "current-sha")
        ledger.client.close()


if __name__ == "__main__":
    unittest.main()
