"""Rolling windows, sent-only memory, update detection and safe artifact cleanup."""

import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from services import news_bot, news_digest
from services import news_memory as memory
from services import telegram_delivery as tg
from tests.test_news_bot import fixture


class NewsMemoryTests(unittest.TestCase):
    def setUp(self):
        self.source = fixture()[0]["items"][0]

    def test_same_title_across_publishers_is_suppressed_but_updates_are_allowed(self):
        history = {"entries": memory.entries_for([self.source], "2026-10-15")}
        syndicated = {
            **self.source,
            "publisher": "Another publisher",
            "url": "https://example.net/syndicated",
        }
        self.assertFalse(memory.unseen(syndicated, history))
        changed = {**self.source, "title": "US inflation falls to 2 percent in a new release"}
        self.assertTrue(memory.unseen(changed, history))
        self.assertEqual(
            memory.url_key(self.source),
            memory.url_key({**self.source, "url": self.source["url"] + "?utm_source=test"}),
        )

    def test_only_presented_sources_are_recorded_not_scraped_candidates(self):
        pack, _ = fixture()
        pack["items"].append({**self.source, "id": "not-presented", "title": "Unselected story"})
        digest = news_bot.summarise(fixture()[0], use_ai=False)
        entries = memory.entries_for(memory.sources_in(digest), "2026-10-15")
        self.assertIn(memory.title_key(self.source), entries)
        self.assertNotIn(memory.title_key(pack["items"][1]), entries)

    def test_history_prunes_active_records_after_fourteen_calendar_days(self):
        class Ledger:
            def get(self, key):
                return {
                    "version": 1,
                    "entries": {
                        "a" * 64: {"sent_on": "2026-10-01"},
                        "b" * 64: {"sent_on": "2026-10-02"},
                        "c" * 64: {"sent_on": "2026-10-15"},
                    },
                }

        history = memory.load(Ledger(), "key", "2026-10-15")
        self.assertNotIn("a" * 64, history["entries"])
        self.assertIn("b" * 64, history["entries"])
        self.assertIn("c" * 64, history["entries"])

    def test_history_reconciles_accepted_claim_without_a_second_send(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
        ):
            ledger = news_bot.LocalLedger()
            delivery = "test-delivery"
            claim_key = hashlib.sha256(delivery.encode()).hexdigest()[:32]
            ledger.reserve(
                claim_key,
                {
                    "status": "pending",
                    "story_entries": memory.entries_for([self.source], "2026-10-15"),
                },
            )
            memory.reconcile(ledger, "history", "2026-10-15", delivery)
            self.assertIsNone(ledger.get("history"))
            ledger.accepted(
                claim_key,
                {
                    "status": "accepted",
                    "story_entries": memory.entries_for([self.source], "2026-10-15"),
                },
            )
            memory.reconcile(ledger, "history", "2026-10-15", delivery)
            self.assertFalse(
                memory.unseen(self.source, memory.load(ledger, "history", "2026-10-15"))
            )

    def test_weekly_excludes_seen_tips_and_unimportant_items(self):
        seen = {"entries": memory.entries_for([self.source], "2026-10-15")}
        major = {
            **self.source,
            "id": "major",
            "title": "Central bank announces historic policy shift",
        }
        tip = {**self.source, "id": "tip", "title": "Top 5 stocks to buy now"}
        result = memory.weekly_candidates({"items": [self.source, major, tip]}, seen)
        self.assertEqual([item["id"] for item in result], ["major"])

    def test_weekly_window_uses_seven_day_search_and_excludes_last_day(self):
        now = datetime(2026, 10, 15, 6, tzinfo=timezone.utc)
        older = {**self.source, "published_at": "2026-10-12T00:00:00+00:00"}
        recent = {
            **self.source,
            "id": "recent",
            "title": "Recent news",
            "published_at": "2026-10-15T00:00:00+00:00",
        }
        expired = {
            **self.source,
            "id": "expired",
            "title": "Expired news",
            "published_at": "2026-10-01T00:00:00+00:00",
        }
        with (
            patch.object(
                news_digest.news_reader,
                "feed",
                return_value={"status": "available", "items": [older, recent, expired]},
            ) as feed,
            patch.object(
                news_digest,
                "direct_feed",
                return_value={"id": "mock", "status": "available", "items": []},
            ),
        ):
            pack = news_digest.collect(
                now, read_articles=False, window_hours=168, older_than_hours=24
            )
        self.assertEqual({item["id"] for item in pack["items"]}, {older["id"]})
        self.assertTrue(all(call.kwargs["days"] == 7 for call in feed.call_args_list))
        self.assertEqual(pack["window_hours"], 168)

    def test_local_cleanup_keeps_recent_unknown_and_claim_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            for name in (
                "2026-10-01-input.json",
                "2026-10-02-digest.json",
                "2026-10-15-email.txt",
                "2026-10-01-claim.json",
                "company-dossier.json",
            ):
                (path / name).write_text("test", encoding="utf-8")
            self.assertEqual(memory.cleanup_local(path, "2026-10-15"), 1)
            self.assertFalse((path / "2026-10-01-input.json").exists())
            self.assertTrue((path / "2026-10-01-claim.json").exists())
            self.assertTrue((path / "company-dossier.json").exists())

    def test_fingerprints_contain_no_plain_titles_urls_or_private_destination(self):
        config = tg.TelegramConfig("123456:" + "x" * 35, "7654321")
        self.assertNotIn(config.chat_id, memory.history_key(config))
        self.assertNotIn(config.token, memory.history_key(config))
        entries = memory.entries_for([self.source], "2026-10-15")
        self.assertTrue(all(len(key) == 64 for key in entries))
        self.assertTrue(
            all(set(value) == {"sent_on", "published_on", "kind"} for value in entries.values())
        )


if __name__ == "__main__":
    unittest.main()
