"""Beginner curriculum scope, grounded expansion and separated delivery."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from services import finance_class as classroom
from services import finance_teacher, news_bot, news_digest
from services import telegram_delivery as tg
from tests.test_news_bot import fixture, provider


class FinanceClassTests(unittest.TestCase):
    def test_full_course_is_broad_and_all_lessons_render(self):
        lessons = classroom.course()
        self.assertEqual(len(lessons), 42)
        self.assertEqual(len({item["module"] for item in lessons}), 7)
        self.assertEqual(len({item["id"] for item in lessons}), 42)
        self.assertEqual(lessons[0]["title"], "What is finance?")
        self.assertTrue(
            {"creation", "financialyear", "quarters", "ipo", "calls", "budgeting", "fx", "fiscal"}
            <= {item["id"] for item in lessons}
        )
        for index in range(42):
            day = (date(2026, 10, 15) + timedelta(days=index)).isoformat()
            with patch.dict("os.environ", {"NEWS_FINANCE_START_DATE": "2026-10-15"}):
                prepared = classroom.prepare(day, use_ai=False)
            messages = classroom.class_messages(prepared)
            self.assertIn("Finance Class", messages[0])
            self.assertNotIn("Stock Daddy", messages[0])
            self.assertTrue(
                all(len(message.encode("utf-16-le")) // 2 <= 4096 for message in messages)
            )
            self.assertIn("<tg-spoiler>", "\n".join(messages))
            self.assertIn('<a href="https://', "\n".join(messages))

    def test_finance_class_and_stock_research_have_distinct_headings(self):
        lesson = finance_teacher.lesson_for_day("2026-10-15", "2026-10-15")
        self.assertIn("Stock Daddy", finance_teacher.heading(lesson))
        self.assertNotIn("Today's learnings", finance_teacher.heading(lesson))

    def test_future_invalid_calendar_and_review_cycle(self):
        with self.assertRaises(news_bot.BotError):
            classroom.lesson_for_day("2026-10-14", "2026-10-15")
        with self.assertRaises(news_bot.BotError):
            classroom.lesson_for_day("not a date", "2026-10-15")
        review = classroom.lesson_for_day("2026-11-26", "2026-10-15")
        self.assertEqual(review["cycle"], 2)
        self.assertEqual(review["id"], "finance")

    def test_no_ai_requires_no_provider_call_and_preserves_full_lesson(self):
        with patch.object(news_bot, "generate_section") as model:
            prepared = classroom.prepare("2026-10-15", use_ai=False)
        model.assert_not_called()
        self.assertIsNone(prepared["explanation"])
        body = "\n".join(classroom.class_messages(prepared))
        self.assertIn("Stock selection is only one small application", body)

    def test_unsupported_ai_numbers_fall_back_to_canonical_content(self):
        lesson = classroom.lesson_for_day("2026-10-15", "2026-10-15")
        source = classroom.lesson_source(lesson, "2026-10-15")
        section = {
            "category": "policy",
            "bullets": [
                {
                    "text": "Banks guarantee 99 percent annual returns.",
                    "why_it_matters": "This claim would require actual evidence.",
                    "support": [
                        {"source_id": source["id"], "quote": "Finance studies how households"}
                    ],
                }
            ],
        }
        with (
            patch.object(news_bot.gemini_rotator, "get_status", return_value={"active_keys": 1}),
            patch.object(
                news_bot.gemini_rotator, "post", return_value=(provider(section), "fake-key")
            ),
            patch.object(news_bot.gemini_rotator, "report_success"),
        ):
            self.assertIsNone(classroom.generate("2026-10-15", [source], "Teach the lesson", True))

    def test_headline_only_never_becomes_a_verified_current_case(self):
        pack, _ = fixture()
        pack["date_ist"] = "2026-10-15"
        prepared = classroom.prepare("2026-10-15", pack, use_ai=False)
        self.assertIsNone(prepared["current"])
        body = "\n".join(classroom.case_messages(prepared))
        self.assertIn("Hypothetical case", body)
        self.assertIn("not a claim", body)
        self.assertNotIn("Keep these terms separate", body)

    def test_current_case_selects_relevant_authored_concepts(self):
        pack, _ = fixture()
        pack["items"][0].update(
            title="Investors face margin calls on leveraged positions",
            read_status="publisher_feed_excerpt",
            evidence_text="A reported article discusses margin calls, leveraged accounts and collateral pressure. "
            * 3,
        )
        prepared = classroom.prepare("2026-10-15", pack, use_ai=False)
        self.assertTrue(
            {"leverage", "calls"} & {concept["id"] for concept in prepared["case_concepts"]}
        )
        body = "\n".join(classroom.case_messages(prepared))
        self.assertIn("Margin call", body)
        self.assertIn("Call option", body)

    def test_margin_case_history_is_dated_allegation_not_recent_identification(self):
        pack, _ = fixture()
        pack["items"][0].update(
            title="Margin pressure affects leveraged investors",
            read_status="publisher_feed_excerpt",
            evidence_text="A reported article describes margin pressure on leveraged investors and funding uncertainty. "
            * 3,
        )
        prepared = classroom.prepare("2026-10-15", pack, use_ai=False)
        self.assertIsNotNone(prepared["current"])
        self.assertIn("alleged", prepared["historical"]["evidence_text"])
        self.assertIn("2021", prepared["historical"]["title"])
        self.assertIn("not a new incident", prepared["historical"]["evidence_text"])
        self.assertIn("not today's cause", "\n".join(classroom.case_messages(prepared)))

    def test_independent_class_and_case_claims_skip_repeat(self):
        config = tg.TelegramConfig("123456:" + "x" * 35, "7654321")
        prepared = classroom.prepare("2026-10-15", use_ai=False)
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(classroom.time, "sleep"),
            patch.object(
                tg,
                "api",
                return_value={"message_id": 12, "chat": {"id": 7654321, "type": "private"}},
            ) as api,
        ):
            ledger = news_bot.LocalLedger()
            self.assertEqual(
                classroom.deliver("2026-10-15", config, ledger, prepared), "telegram_accepted"
            )
            self.assertEqual(
                classroom.deliver("2026-10-15", config, ledger, prepared, context=True),
                "telegram_accepted",
            )
            count = api.call_count
            self.assertEqual(
                classroom.deliver("2026-10-15", config, ledger, prepared), "already_accepted"
            )
            self.assertEqual(
                classroom.deliver("2026-10-15", config, ledger, prepared, context=True),
                "already_accepted",
            )
            self.assertEqual(api.call_count, count)


if __name__ == "__main__":
    unittest.main()
