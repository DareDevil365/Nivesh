"""Source/date checks, bounded synthesis and independent delivery state."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import ai_newsletter as ai
from services import daily_newsletters, news_bot, news_digest
from services import telegram_delivery as tg
from tests.test_news_bot import fixture, provider
from tests.test_newsletter_mail import NOW


def pack():
    return {
        "date_ist": "2026-10-15",
        "items": [
            {
                "id": "primary",
                "title": "A documented AI model release",
                "url": "https://openai.com/news/example",
                "publisher": "OpenAI",
                "published_at": "2026-10-15T00:00:00+00:00",
                "source_kind": "company_announcement",
                "categories": ["policy"],
                "read_status": "publisher_feed_excerpt",
                "evidence_text": "A documented AI model release describes capabilities and limitations. Availability depends on the announced conditions.",
            }
        ],
        "feeds": [],
        "mail": {"status": "no_approved_issues"},
        "article_reads": 0,
    }


class AINewsletterTests(unittest.TestCase):
    def test_valid_synthesis_passes_shared_schema_with_complete_pack_metadata(self):
        candidate = {
            "category": "policy",
            "bullets": [
                {
                    "text": "The publisher describes a model release with stated limitations.",
                    "why_it_matters": "Check its announced conditions before assuming it is available for your use.",
                    "support": [
                        {
                            "source_id": "primary",
                            "quote": "A documented AI model release describes capabilities and limitations.",
                        }
                    ],
                }
            ],
        }
        with (
            patch.object(news_bot.gemini_rotator, "get_status", return_value={"active_keys": 1}),
            patch.object(
                news_bot.gemini_rotator, "post", return_value=(provider(candidate), "fake")
            ) as post,
            patch.object(news_bot.gemini_rotator, "report_success"),
        ):
            result = ai.prepare(pack(), {"version": 1, "entries": {}}, use_ai=True)
        self.assertIsNotNone(result["section"])
        self.assertIn("company_announcement", str(post.call_args))
        self.assertIn("AI-assisted perspective", "\n".join(ai.messages(result)))

    def test_primary_rss_dates_domains_and_excerpts_are_checked(self):
        raw = b"""<rss><channel><item><title>A model release</title><link>https://openai.com/news/test?utm_source=mail</link><pubDate>Thu, 15 Oct 2026 00:00:00 GMT</pubDate><description>A bounded public description.</description></item><item><title>Wrong domain</title><link>https://attacker.example/story</link><pubDate>Thu, 15 Oct 2026 00:00:00 GMT</pubDate></item><item><title>Old</title><link>https://openai.com/news/old</link><pubDate>Thu, 01 Oct 2026 00:00:00 GMT</pubDate></item><item><title>Future</title><link>https://openai.com/news/future</link><pubDate>Thu, 22 Oct 2026 00:00:00 GMT</pubDate></item></channel></rss>"""
        with patch.object(
            ai,
            "fetch_public",
            return_value=(raw, "https://openai.com/news/rss.xml", "application/rss+xml"),
        ):
            result = ai.feed(*ai.FEEDS[0], NOW)
        self.assertEqual(len(result["items"]), 1)
        self.assertNotIn("?", result["items"][0]["url"])
        self.assertEqual(result["items"][0]["read_status"], "publisher_feed_excerpt")

    def test_atom_preprints_remain_unreviewed_and_bad_xml_is_unavailable(self):
        raw = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Research result</title><link href="https://arxiv.org/abs/2610.00001"/><updated>2026-10-15T00:00:00Z</updated><summary>Research abstract, not proof of deployment.</summary></entry></feed>"""
        with patch.object(
            ai,
            "fetch_public",
            return_value=(raw, "https://rss.arxiv.org/rss/cs.AI", "application/atom+xml"),
        ):
            result = ai.feed(*ai.FEEDS[-1], NOW)
        self.assertEqual(result["items"][0]["source_kind"], "preprint_not_peer_reviewed")
        for bad in (b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss/>', b"<html>Not a feed</html>"):
            with patch.object(
                ai, "fetch_public", return_value=(bad, "https://openai.com/", "text/html")
            ):
                self.assertEqual(ai.feed(*ai.FEEDS[0], NOW)["status"], "unavailable")

    def test_selection_represents_email_primary_and_research_without_single_publisher_flood(self):
        base = pack()["items"][0]
        items = [{**base, "id": str(i), "title": str(i)} for i in range(15)]
        items.extend(
            [
                {
                    **base,
                    "id": "mail",
                    "source_kind": "newsletter_commentary",
                    "publisher": "The Batch",
                },
                {
                    **base,
                    "id": "paper",
                    "source_kind": "preprint_not_peer_reviewed",
                    "publisher": "arXiv",
                },
            ]
        )
        selected = ai.select(items)
        self.assertLessEqual(len(selected), 6)
        self.assertLessEqual(sum(i["publisher"] == "OpenAI" for i in selected), 2)
        self.assertTrue({"mail", "paper"} <= {i["id"] for i in selected})

    def test_unsupported_ai_numbers_are_rejected_and_sources_remain(self):
        source = pack()["items"][0]
        candidate = {
            "category": "policy",
            "bullets": [
                {
                    "text": "This model improves all tasks by 999 percent.",
                    "why_it_matters": "This would require evidence not supplied here.",
                    "support": [{"source_id": "primary", "quote": "A documented AI model release"}],
                }
            ],
        }
        with (
            patch.object(news_bot.gemini_rotator, "get_status", return_value={"active_keys": 1}),
            patch.object(
                news_bot.gemini_rotator, "post", return_value=(provider(candidate), "fake")
            ),
            patch.object(news_bot.gemini_rotator, "report_success"),
        ):
            result = ai.prepare(pack(), {"version": 1, "entries": {}}, use_ai=True)
        self.assertIsNone(result["section"])
        self.assertEqual(result["items"][0]["id"], source["id"])

    def test_messages_have_clickable_sources_evidence_labels_and_intact_html(self):
        digest = ai.prepare(pack(), {"version": 1, "entries": {}}, use_ai=False)
        messages = ai.messages(digest)
        self.assertIn("Daily Brief · AI newsletter", messages[0])
        self.assertIn('<a href="https://openai.com/news/example">', "\n".join(messages))
        self.assertIn("company announcement", "\n".join(messages))
        self.assertIn("Source excerpt", "\n".join(messages))
        self.assertTrue(all(len(m.encode("utf-16-le")) // 2 <= 4096 for m in messages))
        digest["items"][0]["url"] = "javascript:alert(1)"
        with self.assertRaises(news_bot.BotError):
            ai.messages(digest)

    def test_independent_claim_skips_collection_and_model_on_repeat(self):
        config = tg.TelegramConfig("123456:" + "x" * 35, "7654321")
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(news_digest, "DIGEST_DIR", Path(folder)),
            patch.object(ai.time, "sleep"),
            patch.object(ai, "collect", return_value=pack()) as collect,
            patch.object(
                tg,
                "api",
                return_value={"message_id": 12, "chat": {"id": 7654321, "type": "private"}},
            ) as api,
        ):
            ledger = news_bot.LocalLedger()
            self.assertEqual(
                ai.deliver("2026-10-15", config, ledger, use_ai=False), "telegram_accepted"
            )
            count = api.call_count
            self.assertEqual(
                ai.deliver("2026-10-15", config, ledger, use_ai=False), "already_accepted"
            )
            self.assertEqual(api.call_count, count)
            collect.assert_called_once()

    def test_offline_collection_does_not_read_mail_or_fetch_web(self):
        with patch.object(ai.newsletter_mail, "collect") as mail, patch.object(ai, "feed") as feed:
            result = ai.collect(NOW, offline=True)
        mail.assert_not_called()
        feed.assert_not_called()
        self.assertEqual(result["mail"]["status"], "offline_not_read")

    def test_ai_edition_precedes_closing_and_failure_withholds_cta(self):
        _, section = fixture()
        digest = news_bot.summarise(fixture()[0], use_ai=False)
        digest["date_ist"] = "2026-10-15"
        order = []
        config = tg.TelegramConfig("123456:" + "x" * 35, "7654321")
        with (
            patch.object(daily_newsletters.time, "sleep"),
            patch.object(
                daily_newsletters.news_memory, "load", return_value={"version": 1, "entries": {}}
            ),
            patch.object(daily_newsletters.news_memory, "reconcile"),
            patch.object(tg, "deliver_messages", return_value="already_accepted"),
            patch.object(
                daily_newsletters.finance_class, "deliver", return_value="already_accepted"
            ),
            patch.object(
                daily_newsletters.finance_teacher, "deliver", return_value="already_accepted"
            ),
            patch.object(
                ai,
                "deliver",
                side_effect=lambda *a, **kw: order.append("ai") or "telegram_accepted",
            ),
            patch.object(
                daily_newsletters,
                "closing",
                side_effect=lambda *a, **kw: order.append("closing") or "telegram_accepted",
            ),
        ):
            result = daily_newsletters.deliver(digest, config, object(), include_ai=True)
            with patch.object(ai, "deliver", side_effect=news_bot.BotError("uncertain")):
                failed = daily_newsletters.deliver(digest, config, object(), include_ai=True)
        self.assertEqual(result["status"], "telegram_accepted")
        self.assertEqual(order, ["ai", "closing"])
        self.assertEqual(failed["status"], "partial_delivery")
        self.assertEqual(failed["editions"]["closing"], "withheld_incomplete_bundle")
