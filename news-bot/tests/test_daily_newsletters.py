"""Edition routing, separate headings, failure isolation and bounded evidence."""

import hashlib
import html
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import daily_newsletters as daily
from services import finance_teacher, news_bot, news_digest
from services import telegram_delivery as tg
from tests.test_news_bot import fixture, provider


class DailyNewsletterTests(unittest.TestCase):
    def setUp(self):
        self.config = tg.TelegramConfig("123456:" + "x" * 35, "7654321")
        self.digest = news_bot.summarise(fixture()[0], use_ai=False)

    def test_finance_and_general_news_are_routed_to_four_distinct_editions(self):
        base = self.digest["sections"][0]
        self.digest["sections"] = [
            {
                **base,
                "id": category,
                "label": category,
                "bullets": [{**base["bullets"][0], "text": "unique-" + category}],
            }
            for category in ("us", "india", "world_general", "india_general")
        ]
        for _edition, title, categories in daily.EDITIONS:
            messages = daily.edition_messages(self.digest, title, categories)
            self.assertIn(title, html.unescape(messages[0]))
            self.assertIn("Wednesday, 14 October 2026", messages[0])
            self.assertNotIn("Why it may matter", messages[0])
            content = "\n".join(messages[1:])
            for section in self.digest["sections"]:
                self.assertEqual(
                    "\n\nunique-" + section["id"] + "\n\n" in content, section["id"] in categories
                )
            self.assertIn('href="https://example.com/story"', content)

    def test_empty_edition_reports_gap_instead_of_nothing_happened(self):
        messages = daily.edition_messages(self.digest, "India general news", {"india_general"})
        self.assertEqual(len(messages), 2)
        self.assertIn("does not establish that nothing happened", messages[1])

    def test_success_order_headings_content_teacher_and_one_closing(self):
        sent = []

        def send(day, messages, config, ledger, identifier):
            sent.append((identifier, messages))
            return "telegram_accepted"

        def teach(*args):
            sent.append(("lesson", ["Today's learnings", "lesson body"]))
            return "telegram_accepted"

        with (
            patch.object(tg, "deliver_messages", side_effect=send),
            patch.object(finance_teacher, "deliver", side_effect=teach),
            patch.object(daily.time, "sleep"),
        ):
            result = daily.deliver(self.digest, self.config, object())
        self.assertEqual(result["status"], "telegram_accepted")
        self.assertEqual(len(sent), 6)
        self.assertIn("World news &amp; finance", sent[0][1][0])
        self.assertIn("India news &amp; finance", sent[1][1][0])
        self.assertEqual(sent[4][0], "lesson")
        self.assertIn("Your next step", sent[5][1][0])

    def test_one_failed_edition_does_not_block_others_or_teacher_and_withholds_cta(self):
        def send(day, messages, config, ledger, identifier):
            if "world_finance-" in identifier:
                raise news_bot.BotError("uncertain")
            return "telegram_accepted"

        with (
            patch.object(tg, "deliver_messages", side_effect=send) as delivery,
            patch.object(finance_teacher, "deliver", return_value="telegram_accepted") as teacher,
            patch.object(daily.time, "sleep"),
        ):
            result = daily.deliver(self.digest, self.config, object())
        self.assertEqual(delivery.call_count, 4)
        teacher.assert_called_once()
        self.assertEqual(result["editions"]["india_general"], "telegram_accepted")
        self.assertEqual(result["status"], "partial_delivery")
        self.assertEqual(result["editions"]["closing"], "withheld_incomplete_bundle")

    def test_all_news_claims_must_be_accepted_before_cli_skips_collection(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
        ):
            ledger = news_bot.LocalLedger()
            for edition, _, _ in daily.EDITIONS:
                self.assertIsNone(daily.existing_delivery("2026-10-14", self.config, ledger))
                key = hashlib.sha256(
                    daily.identifier("2026-10-14", self.config, edition).encode()
                ).hexdigest()[:32]
                ledger.reserve(key, {"status": "accepted"})
            self.assertEqual(
                daily.existing_delivery("2026-10-14", self.config, ledger), "already_accepted"
            )

    def test_selection_excludes_stock_tips_and_bounds_input_with_diversity(self):
        source = fixture()[0]["items"][0]
        items = [
            {**source, "id": str(index), "publisher": "one" if index < 15 else "two"}
            for index in range(25)
        ]
        items.append({**source, "id": "tips", "title": "Top 5 stocks to buy now"})
        selected = news_bot.select_evidence(items, "us")
        self.assertEqual(len(selected), 12)
        self.assertNotIn("tips", {item["id"] for item in selected})
        self.assertEqual({item["publisher"] for item in selected}, {"one", "two"})

    def test_ai_obvious_price_predictions_and_nonobject_output_are_rejected(self):
        pack, section = fixture()
        section["bullets"][0]["text"] = "US stock prices will definitely rise after this report."
        for candidate in (section, ["invalid structure"]):
            with (
                patch.object(
                    news_bot.gemini_rotator, "get_status", return_value={"active_keys": 1}
                ),
                patch.object(
                    news_bot.gemini_rotator, "post", return_value=(provider(candidate), "fake-key")
                ),
                patch.object(news_bot.gemini_rotator, "report_success"),
            ):
                self.assertIsNone(news_bot.generate_section(pack, "us", pack["items"]))

    def test_feed_empty_description_is_headline_only_and_xml_entities_fail(self):
        raw = b"<rss><channel><item><title>India reports economic release</title><link>https://example.com/report</link><pubDate>Thu, 15 Oct 2026 00:00:00 GMT</pubDate></item></channel></rss>"
        with patch.object(news_digest.news_reader, "_fetch", return_value=raw):
            result = news_digest.direct_feed("Publisher", "https://example.com/rss", "india")
            self.assertEqual(result["items"][0]["read_status"], "headline_only")
        with patch.object(
            news_digest.news_reader,
            "_fetch",
            return_value=b'<!DOCTYPE rss [<!ENTITY xx "x">]>' + raw,
        ):
            self.assertEqual(
                news_digest.direct_feed("Publisher", "https://example.com/rss", "india")["status"],
                "unavailable",
            )

    def test_general_news_keeps_category_and_sources_in_validated_fallback(self):
        pack, _ = fixture()
        pack["items"][0]["categories"] = ["world_general"]
        pack["items"][0]["title"] = "World leaders announce international education summit"
        result = news_bot.summarise(pack, use_ai=False)
        self.assertEqual(result["sections"][0]["id"], "world_general")
        self.assertEqual(result["summary_modes"]["world_general"], "headline_fallback")


if __name__ == "__main__":
    unittest.main()
