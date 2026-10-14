"""Deterministic course coverage, calendar pacing and independent send claims."""

import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from services import finance_teacher as teacher
from services import news_bot, news_digest
from services import telegram_delivery as tg
from tests.test_news_bot import fixture


class FinanceTeacherTests(unittest.TestCase):
    def setUp(self):
        self.config = tg.TelegramConfig("123456:" + "x" * 35, "7654321")

    def test_all_47_lessons_render_with_sources_examples_and_self_checks(self):
        lessons = teacher.course()
        self.assertEqual(len(lessons), 47)
        self.assertEqual(len({lesson["id"] for lesson in lessons}), 47)
        beginning = date(2026, 10, 15)
        for index, lesson in enumerate(lessons):
            day = (beginning + timedelta(days=index)).isoformat()
            selected = teacher.lesson_for_day(day, "2026-10-15")
            self.assertEqual(selected["id"], lesson["id"])
            rendered = teacher.render(selected)
            self.assertLessEqual(len(rendered.encode("utf-16-le")) // 2, 4096)
            self.assertIn("<tg-spoiler>", rendered)
            self.assertIn('<a href="https://', rendered)
            self.assertIn("Worked example / research case", rendered)
            self.assertIn("Try it in your research", rendered)
            self.assertIn("does not grade replies", rendered)
            if lesson.get("options"):
                self.assertTrue(0 <= lesson["answer"] < len(lesson["options"]))

    def test_day_one_sequence_leap_date_and_explicit_review_cycle(self):
        self.assertEqual(teacher.lesson_for_day("2026-10-15", "2026-10-15")["id"], "business")
        self.assertEqual(teacher.lesson_for_day("2026-10-16", "2026-10-15")["id"], "evidence")
        self.assertEqual(teacher.lesson_for_day("2028-02-29", "2028-02-28")["day"], 2)
        review_day = (date(2026, 10, 15) + timedelta(days=47)).isoformat()
        review = teacher.lesson_for_day(review_day, "2026-10-15")
        self.assertEqual(review["cycle"], 2)
        self.assertEqual(review["id"], "business")
        self.assertIn("review cycle 2", teacher.render(review))
        for day, start in (
            ("wrong", "2026-10-15"),
            ("2026-10-15", "wrong"),
            ("2026-10-14", "2026-10-15"),
        ):
            with self.assertRaises(news_bot.BotError):
                teacher.lesson_for_day(day, start)

    def test_hypothetical_arithmetic_and_units_are_consistent(self):
        self.assertAlmostEqual(110 * 9.5, 1045)
        self.assertAlmostEqual((11 * 16 / (10 * 20) - 1) * 100, -12)
        self.assertIn("₹1,045", teacher.EXAMPLES["drivers"])
        self.assertIn("12%", teacher.EXAMPLES["valuation"])
        self.assertIn("₹10", teacher.EXAMPLES["EPS"])
        self.assertIn("25 basis points", teacher.EXAMPLES["Basis point"])
        self.assertIn("100%", teacher.EXAMPLES["Drawdown"])

    def test_optional_news_link_is_labelled_as_practice_not_confirmed_impact(self):
        pack, _ = fixture()
        digest = news_bot.summarise(pack, use_ai=False)
        lesson = teacher.lesson_for_day("2026-10-15", "2026-10-15")
        rendered = teacher.render(lesson, digest)
        self.assertNotIn("Optional news exercise", rendered)
        digest["sections"][0]["bullets"][0]["text"] = "A company reports new sales figures."
        rendered = teacher.render(lesson, digest)
        self.assertIn("Optional news exercise", rendered)
        self.assertIn("no company impact is established", rendered)
        self.assertIn("headline only", rendered)
        self.assertIn('href="https://example.com/story"', rendered)

    def test_teacher_claim_is_separate_from_news_and_repeat_skips(self):
        day = "2026-10-15"
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(teacher.time, "sleep"),
            patch.object(
                tg,
                "api",
                return_value={"message_id": 12, "chat": {"id": 7654321, "type": "private"}},
            ) as api,
        ):
            ledger = news_bot.LocalLedger()
            news_key = hashlib.sha256(self.config.delivery_id(day).encode()).hexdigest()[:32]
            ledger.reserve(news_key, {"status": "accepted"})
            with patch.dict("os.environ", {"NEWS_LEARNING_START_DATE": day}):
                self.assertEqual(teacher.deliver(day, self.config, ledger), "telegram_accepted")
                self.assertEqual(teacher.deliver(day, self.config, ledger), "already_accepted")
            self.assertEqual(api.call_count, 1)
            self.assertIn("Daily finance teacher", api.call_args.kwargs["data"]["text"])
            self.assertEqual(ledger.get(news_key)["status"], "accepted")

    def test_failed_teacher_send_does_not_replay_or_change_news_claim(self):
        day = "2026-10-15"
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(teacher.time, "sleep"),
            patch.object(tg, "api", side_effect=news_bot.BotError("uncertain")) as api,
            patch.dict("os.environ", {"NEWS_LEARNING_START_DATE": day}),
        ):
            ledger = news_bot.LocalLedger()
            for _ in range(2):
                with self.assertRaises(news_bot.BotError):
                    teacher.deliver(day, self.config, ledger)
            self.assertEqual(api.call_count, 1)

    def cli(self):
        path = Path(__file__).resolve().parents[1] / "scripts/standalone_news.py"
        spec = importlib.util.spec_from_file_location("standalone_teacher_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_cli_already_sent_news_only_attempts_the_pending_teacher(self):
        cli = self.cli()
        output = io.StringIO()
        with (
            patch("sys.argv", ["standalone_news.py"]),
            patch.dict("os.environ", {"NEWS_DELIVERY": "telegram"}),
            patch.object(tg.TelegramConfig, "load", return_value=self.config),
            patch.object(tg, "existing_delivery", return_value="already_accepted"),
            patch.object(tg, "check"),
            patch.object(teacher, "deliver", return_value="telegram_accepted") as lesson,
            patch.object(news_digest, "collect") as collect,
            patch.object(news_bot, "summarise") as summarise,
            patch.object(tg, "deliver") as news,
            contextlib.redirect_stdout(output),
        ):
            cli.main()
        collect.assert_not_called()
        summarise.assert_not_called()
        news.assert_not_called()
        lesson.assert_called_once()
        self.assertEqual(json.loads(output.getvalue())["daily_teacher"], "telegram_accepted")

    def test_dry_run_uses_no_delivery_credentials_or_teacher_send(self):
        cli = self.cli()
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "pack.json"
            source.write_text(json.dumps(fixture()[0]), encoding="utf-8")
            with (
                patch(
                    "sys.argv",
                    ["standalone_news.py", "--dry-run", "--no-ai", "--input", str(source)],
                ),
                patch.dict("os.environ", {"NEWS_DELIVERY": "telegram"}),
                patch.object(news_digest, "DIGEST_DIR", Path(folder)),
                patch.object(tg.TelegramConfig, "load") as load,
                patch.object(tg, "api") as api,
                patch.object(teacher, "deliver") as lesson,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                cli.main()
            load.assert_not_called()
            api.assert_not_called()
            lesson.assert_not_called()


if __name__ == "__main__":
    unittest.main()
