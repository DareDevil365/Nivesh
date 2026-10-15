"""Beginner curriculum scope, grounded expansion and separated delivery."""

import copy
import re
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from services import finance_class as classroom
from services import finance_teacher, finance_textbook, news_bot, news_digest
from services import telegram_delivery as tg
from tests.test_news_bot import fixture, provider


class FinanceClassTests(unittest.TestCase):
    def test_every_lesson_has_substantive_authored_teaching_without_ai(self):
        class Markup(HTMLParser):
            def __init__(self):
                super().__init__()
                self.opened = []

            def handle_starttag(self, tag, attrs):
                self.assert_tag(tag)
                self.opened.append(tag)

            def handle_endtag(self, tag):
                if not self.opened or self.opened.pop() != tag:
                    raise AssertionError("Unbalanced Telegram markup")

            def assert_tag(self, tag):
                if tag not in {"b", "i", "a", "tg-spoiler"}:
                    raise AssertionError("Unsupported Telegram markup")

        with patch.dict("os.environ", {"NEWS_FINANCE_START_DATE": "2026-10-15"}):
            for index in range(42):
                day = (date(2026, 10, 15) + timedelta(days=index)).isoformat()
                prepared = classroom.prepare(day, use_ai=False)
                messages = classroom.class_messages(prepared)
                body = "\n".join(messages)
                # Check delivered pedagogy, not merely presence of data fields.
                self.assertGreaterEqual(finance_textbook.word_count(messages), 2400)
                self.assertLessEqual(finance_textbook.word_count(messages), 3200)
                self.assertLessEqual(len(messages), 20)
                estimate = int(re.search(r"about (\d+) min reading", body).group(1))
                self.assertGreaterEqual(estimate, 15)
                self.assertLessEqual(estimate, 20)
                for label in (
                    "By the end",
                    "Words you will use",
                    "How it works · Step 3",
                    "Worked example · Step 3",
                    "Where people get confused",
                    "Your turn",
                    "Worked solution",
                    "Use it outside this lesson",
                    "Textbook reading",
                    "Extended hypothetical case",
                    "Supporting reading",
                ):
                    self.assertIn(label, body)
                self.assertLess(
                    body.index("How it works · Step 1"), body.index("Worked example · Step 1")
                )
                self.assertLess(body.index("Your turn"), body.index("Worked solution"))
                for number, message in enumerate(messages[1:], 1):
                    self.assertIn(f"Part {number}/{len(messages) - 1}", message)
                    self.assertLessEqual(len(message.encode("utf-16-le")) // 2, 4096)
                    parser = Markup()
                    parser.feed(message)
                    parser.close()
                    self.assertEqual(parser.opened, [])

    def test_missing_or_incomplete_depth_fails_instead_of_sending_shallow_lesson(self):
        broken = copy.deepcopy(classroom.DEPTH)
        del broken["money"]
        with patch.object(classroom, "DEPTH", broken), self.assertRaises(news_bot.BotError):
            classroom.course()

        broken = copy.deepcopy(classroom.DEPTH)
        broken["finance"]["worked"] = ["Only a definition"]
        with patch.object(classroom, "DEPTH", broken), self.assertRaises(news_bot.BotError):
            classroom.course()

    def test_textbook_rejects_missing_coverage_and_unrelated_or_self_connections(self):
        broken = copy.deepcopy(finance_textbook.DATA)
        del broken["connections"]["money"]
        with patch.object(finance_textbook, "DATA", broken), self.assertRaises(news_bot.BotError):
            finance_textbook.validate(classroom.course())
        for value in ("finance", "not-a-lesson"):
            broken = copy.deepcopy(finance_textbook.DATA)
            broken["connections"]["finance"][0] = value
            with (
                patch.object(finance_textbook, "DATA", broken),
                self.assertRaises(news_bot.BotError),
            ):
                finance_textbook.validate(classroom.course())

    def test_textbook_does_not_fake_reading_time_with_an_incomplete_chapter(self):
        lesson = classroom.lesson_for_day("2026-10-15", "2026-10-15")
        with (
            patch.object(finance_textbook, "MIN_WORDS", 100000),
            self.assertRaises(news_bot.BotError),
        ):
            finance_textbook.chapter_blocks(
                lesson, classroom.course(), classroom.DATA["sources"], 500
            )

    def test_textbook_escapes_prose_and_rejects_unsafe_connected_source(self):
        lesson = classroom.lesson_for_day("2026-10-15", "2026-10-15")
        data = copy.deepcopy(finance_textbook.DATA)
        data["modules"][0]["foundation"][0] += ' <script>alert("bad")</script>'
        with patch.object(finance_textbook, "DATA", data):
            blocks = finance_textbook.chapter_blocks(
                lesson, classroom.course(), classroom.DATA["sources"], 500
            )
        text = "\n".join(blocks)
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)
        sources = copy.deepcopy(classroom.DATA["sources"])
        sources["money"]["url"] = "javascript:alert(1)"
        with self.assertRaises(news_bot.BotError):
            finance_textbook.chapter_blocks(lesson, classroom.course(), sources, 500)

    def test_spaced_recall_uses_previous_and_week_old_topics_not_assumed_performance(self):
        first = classroom.lesson_for_day("2026-10-15", "2026-10-15")
        self.assertEqual(classroom.recall_questions(first), [])
        second = classroom.lesson_for_day("2026-10-16", "2026-10-15")
        self.assertEqual([q["id"] for q in classroom.recall_questions(second)], ["finance"])
        eighth = classroom.lesson_for_day("2026-10-22", "2026-10-15")
        self.assertEqual([q["taught_day"] for q in classroom.recall_questions(eighth)], [7, 1])
        review = classroom.lesson_for_day("2026-11-26", "2026-10-15")
        self.assertEqual([q["taught_day"] for q in classroom.recall_questions(review)], [42, 36])

    def test_authored_exercise_arithmetic_against_independent_calculations(self):
        d = Decimal
        calculations = {
            "finance": [8000 + 2000 - 6000 - 3000],
            "money": [720 // 40],
            "flows": [9000 + 3000 - 2000, 4000 + 3000, 9000 - 4000 - 2000],
            "budgeting": [3000 - 2000 - 2000 + 5000],
            "interest": [5000 * d(".08") * d(".25")],
            "compounding": [2000 * d("1.05") ** 2, 2000 * d("1.05") ** 2 - 2200],
            "timevalue": [1210 / d("1.1") ** 2],
            "inflation": [(d(220) / 200 - 1) * 100, (d(231) / 220 - 1) * 100],
            "realnominal": [((d("1.2") / d("1.1") - 1) * 100).quantize(d(".01"))],
            "primarysecondary": [100],
            "orders": [3 * 50 + 55, d(3 * 50 + 55) / 4],
            "quarters": [(d(120) / 100 - 1) * 100, (d(120) / 150 - 1) * 100],
            "statements": [50 - 30],
            "accrual": [600 // 6 * 2, 600 - 600 // 6 * 2],
            "balance": [(500 + 100) - (320 + 100)],
            "cashprofit": [30 + 5 - 10, 30 + 5 - 10 - 20],
            "equity": [(98 + 4 - 100) * 100 // 100],
            "bonds": [40 * 100 // 1000],
            "yields": [d(120) / d("1.2"), d(120) / d("1.25")],
            "calls": [52 - 50, 52 - 50 - 4],
            "leverage": [80 - 60, (40 - (80 - 60)) * 100 // 40],
            "fx": [(200 - 150) * (84 - 80)],
            "fiscal": [110 - 90],
        }
        for topic, values in calculations.items():
            answer = classroom.DEPTH[topic]["exercise"]["answer"].replace(",", "")
            # Negative outcomes are expressed in prose as well as equations.
            numbers = {abs(d(token)) for token in re.findall(r"-?\d+(?:\.\d+)?", answer)}
            for value in values:
                self.assertIn(abs(d(value)), numbers, (topic, value, answer))

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
