"""Compact reading budgets, independent HTML mail delivery and external timing."""

import importlib.util
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from services import (
    ai_newsletter as ai,
)
from services import brief_format as brief
from services import (
    daily_newsletters as daily,
)
from services import delivery_time as clock
from services import detailed_report as report
from services import (
    finance_class,
    news_bot,
    news_digest,
)
from services import telegram_delivery as tg
from tests.test_ai_newsletter import pack as ai_pack
from tests.test_news_bot import fixture


class BriefDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.digest = news_bot.summarise(fixture()[0], use_ai=False)
        self.day = "2026-10-16"
        self.digest["date_ist"] = self.day

    def test_all_five_news_sections_and_weekly_fit_five_minute_budget(self):
        base = self.digest["sections"][0]
        sentence = " ".join(["meaningful"] * 34) + "."
        why = " ".join(["conditional"] * 11) + "."
        self.digest["sections"] = [
            {
                **base,
                "id": category,
                "bullets": [
                    {**base["bullets"][0], "text": sentence + " " + str(i), "why_it_matters": why}
                    for i in range(4)
                ],
            }
            for category in ("us", "india", "world_general", "india_general")
        ]
        messages = []
        for _, title, categories in daily.EDITIONS:
            part = daily.edition_messages(self.digest, title, categories, compact=True)
            self.assertEqual(len(part), 1)
            messages.extend(part)
        a = ai.prepare(ai_pack(), {"version": 1, "entries": {}}, use_ai=False)
        messages.extend(ai.messages(a, compact=True))
        messages.extend(
            daily.weekly_messages([fixture()[0]["items"][0]] * 4, self.day, compact=True)
        )
        words = len(BeautifulSoup("\n".join(messages), "html.parser").get_text(" ").split())
        self.assertLessEqual(words, 800)
        self.assertTrue(all(len(m.encode("utf-16-le")) // 2 < 4096 for m in messages))
        self.assertNotIn("Collection coverage", "\n".join(messages))
        self.assertIn("href=", "\n".join(messages))

    def test_long_sentences_fall_back_to_whole_headline_not_mid_claim_cut(self):
        text = " ".join(["precondition"] * 80) + " not confirmed."
        self.assertEqual(brief.sentence(text, 35, "Attributed headline."), "Attributed headline.")
        self.assertEqual(
            brief.sentence("A complete first sentence. " + text, 35, "Fallback"),
            "A complete first sentence.",
        )

    def test_compact_story_memory_excludes_stories_not_displayed(self):
        b = self.digest["sections"][0]["bullets"][0]
        self.digest["sections"][0]["bullets"] = [
            {
                **b,
                "text": f"Unique story {i} with important factual details.",
                "sources": [{**b["sources"][0], "id": str(i), "url": f"https://example.com/{i}"}],
            }
            for i in range(4)
        ]
        self.assertEqual({s["id"] for s in brief.sources_in(self.digest, {"us"})}, {"0", "1"})

    def test_duplicate_bullets_are_not_repeated(self):
        b = self.digest["sections"][0]["bullets"][0]
        self.digest["sections"][0]["bullets"] = [b, b, b]
        self.assertEqual(len(brief.select(self.digest, {"us"})), 1)

    def test_unsafe_compact_citation_is_rejected(self):
        self.digest["sections"][0]["bullets"][0]["sources"][0]["url"] = "javascript:bad()"
        with self.assertRaises(news_bot.BotError):
            daily.edition_messages(self.digest, "World news & finance", {"us"}, compact=True)

    def test_detailed_email_is_html_with_real_links_and_full_research(self):
        a = ai.prepare(ai_pack(), {"version": 1, "entries": {}}, use_ai=False)
        result = report.build(self.day, self.digest, [], a)
        self.assertIn('<a href="https://example.com/story"', result["html"])
        self.assertIn("https://example.com/story", result["text"])
        self.assertIn("Daily Brief · AI newsletter", result["html"])
        self.assertIn("Reading notes", result["html"])
        self.assertNotIn("password", result["html"])

    def test_report_uses_its_own_id_not_the_legacy_mail_or_telegram_claim(self):
        config = report.ReportConfig("sender@gmail.com", "private", "reader@example.com")
        legacy = news_bot.MailConfig("sender@gmail.com", "private", "reader@example.com")
        self.assertNotEqual(config.message_id(self.day), legacy.message_id(self.day))
        self.assertNotIn("reader@example.com", config.message_id(self.day))

    def test_smtp_sends_multipart_html_to_only_configured_recipient(self):
        config = report.ReportConfig("sender@gmail.com", "private", "reader@example.com")
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.send_message.return_value = {}
        with patch.object(report.smtplib, "SMTP_SSL", return_value=smtp):
            report.send(
                config,
                {
                    "subject": "A report",
                    "html": '<a href="https://example.com">Source</a>',
                    "text": "Source https://example.com",
                },
                config.message_id(self.day),
            )
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message.get_body(preferencelist=("html",)).get_content_type(), "text/html")
        self.assertEqual(smtp.send_message.call_args.kwargs["to_addrs"], ["reader@example.com"])
        self.assertNotIn("private", message.as_string())

    def test_report_acceptance_skips_repeat_without_smtp_or_sent_lookup(self):
        config = report.ReportConfig("sender@gmail.com", "private", "reader@example.com")
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(news_bot, "sent_message_exists", return_value=False) as sent,
            patch.object(report, "send") as send,
        ):
            ledger = news_bot.LocalLedger()
            self.assertEqual(
                report.deliver(self.day, {"subject": "Report"}, ledger, config), "smtp_accepted"
            )
            self.assertEqual(
                report.deliver(self.day, {"subject": "Report"}, ledger, config), "already_accepted"
            )
            send.assert_called_once()
            sent.assert_called_once()

    def test_new_email_report_does_not_replay_accepted_telegram_or_recollect_on_retry(self):
        import hashlib

        config = tg.TelegramConfig("123456:" + "x" * 35, "7654321")
        mail = report.ReportConfig("sender@gmail.com", "private", "reader@example.com")
        a = ai_pack()
        a["date_ist"] = self.day
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(news_bot, "sent_message_exists", return_value=False),
            patch.object(report.ReportConfig, "load", return_value=mail),
            patch.object(report, "send") as send,
            patch.object(ai, "collect", return_value=a) as collect,
            patch.object(tg, "api") as api,
            patch.object(daily.time, "sleep"),
            patch.object(ai.time, "sleep"),
            patch.dict(os.environ, {"NEWS_BRIEF_MODE": "short"}),
        ):
            ledger = news_bot.LocalLedger()
            ids = [
                daily.identifier(self.day, config, e)
                for e in [x[0] for x in daily.EDITIONS] + ["weekly", "closing"]
            ]
            ids += [
                finance_class.CLASS_VERSION + config.delivery_id(self.day),
                "finance-context-v1-" + config.delivery_id(self.day),
                "stock-daddy-v1-" + config.delivery_id(self.day),
                "daily-brief-ai-v1-" + config.delivery_id(self.day),
            ]
            for identifier in ids:
                ledger.reserve(
                    hashlib.sha256(identifier.encode()).hexdigest()[:32], {"status": "accepted"}
                )
            first = daily.deliver(
                self.digest, config, ledger, include_ai=True, ai_use_ai=False, include_report=True
            )
            second = daily.deliver(
                self.digest, config, ledger, include_ai=True, ai_use_ai=False, include_report=True
            )
            self.assertEqual(first["editions"]["detailed_email"], "smtp_accepted")
            self.assertEqual(second["editions"]["detailed_email"], "already_accepted")
            send.assert_called_once()
            collect.assert_called_once()
            api.assert_not_called()

    def test_missing_ai_report_withholds_incomplete_email_without_stopping_news(self):
        config = tg.TelegramConfig("123456:" + "x" * 35, "7654321")
        with (
            patch.object(report, "existing", return_value=None),
            patch.object(report, "deliver") as email,
            patch.object(tg, "deliver_messages", return_value="already_accepted"),
            patch.object(daily.news_memory, "load", return_value={"version": 1, "entries": {}}),
            patch.object(daily.news_memory, "reconcile"),
            patch.object(daily.finance_class, "deliver", return_value="already_accepted"),
            patch.object(daily.finance_teacher, "deliver", return_value="already_accepted"),
            patch.object(
                ai, "deliver", side_effect=news_bot.BotError("AI source collection unavailable")
            ),
            patch.object(daily.time, "sleep"),
        ):
            result = daily.deliver(
                self.digest, config, object(), include_ai=True, include_report=True
            )
        self.assertEqual(result["editions"]["world_finance"], "already_accepted")
        self.assertEqual(result["editions"]["detailed_email"], "withheld_missing_ai_report")
        email.assert_not_called()

    def test_ambiguous_smtp_is_not_blindly_retried(self):
        config = report.ReportConfig("sender@gmail.com", "private", "reader@example.com")
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(news_bot, "sent_message_exists", return_value=False),
            patch.object(report, "send", side_effect=news_bot.BotError("Ambiguous SMTP")) as send,
        ):
            ledger = news_bot.LocalLedger()
            for _ in range(2):
                with self.assertRaises(news_bot.BotError):
                    report.deliver(self.day, {}, ledger, config)
            send.assert_called_once()

    def test_pending_mail_can_reconcile_against_sent_without_resending(self):
        config = report.ReportConfig("sender@gmail.com", "private", "reader@example.com")
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(news_bot, "sent_message_exists", return_value=True),
            patch.object(report, "send") as send,
        ):
            ledger = news_bot.LocalLedger()
            self.assertEqual(report.deliver(self.day, {}, ledger, config), "already_in_sent")
            send.assert_not_called()

    def test_reading_mode_does_not_shorten_finance_class(self):
        with patch.dict(
            os.environ, {"NEWS_BRIEF_MODE": "short", "NEWS_FINANCE_START_DATE": "2026-10-15"}
        ):
            teaching = finance_class.prepare("2026-10-16", use_ai=False)
            messages = finance_class.class_messages(teaching)
        words = len(BeautifulSoup(" ".join(messages), "html.parser").get_text(" ").split())
        self.assertGreater(words, 2400)
        self.assertGreater(len(messages), 2)

    def test_early_hold_waits_in_short_steps_and_late_run_never_waits_tomorrow(self):
        first = datetime(2026, 10, 16, 0, 10, tzinfo=timezone.utc)
        final = first + timedelta(minutes=20)
        with patch.dict(os.environ, {"NEWS_HOLD_UNTIL_6AM": "true"}):
            sleep = MagicMock()
            times = iter([first, final])
            clock.wait_until_six(now=lambda: next(times), sleep=sleep)
            sleep.assert_called_once_with(30)
            sleep.reset_mock()
            clock.wait_until_six(now=lambda: final + timedelta(hours=4), sleep=sleep)
            sleep.assert_not_called()
            with self.assertRaises(news_bot.BotError):
                clock.wait_until_six(now=lambda: first - timedelta(hours=1), sleep=sleep)

    def test_external_schedule_uses_ist_and_dry_run_check_without_broad_git_credential(self):
        path = Path(__file__).resolve().parents[1] / "scripts/setup_scheduler.py"
        spec = importlib.util.spec_from_file_location("scheduler_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = module.job_payload("limited-private", 5, 40, "Morning")
        self.assertEqual(payload["schedule"]["timezone"], "Asia/Kolkata")
        self.assertEqual(payload["schedule"]["hours"], [5])
        self.assertEqual(payload["schedule"]["minutes"], [40])
        self.assertEqual(payload["requestMethod"], 1)
        self.assertTrue(json.loads(payload["extendedData"]["body"])["inputs"]["hold_until_six"])
        self.assertFalse(payload["saveResponses"])
        self.assertNotIn("git credential", path.read_text())


if __name__ == "__main__":
    unittest.main()
