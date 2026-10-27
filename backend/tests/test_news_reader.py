import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient

from main import app
from services import news_reader as news

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def rss(items):
    return (
        "<rss><channel>"
        + "".join(
            f"<item><title>{title}</title><link>{url}</link><pubDate>{when}</pubDate><source url='https://publisher.example'>{publisher}</source></item>"
            for title, url, when, publisher in items
        )
        + "</channel></rss>"
    ).encode()


class NewsParsingTests(unittest.TestCase):
    def test_source_title_dates_and_unverified_status(self):
        body = rss(
            [
                (
                    "Hy-Tech Engineers earnings - Publisher",
                    "https://news.google.com/rss/articles/id",
                    "Wed, 14 Oct 2026 09:00:00 GMT",
                    "Publisher",
                )
            ]
        )
        items, skipped, count = news.parse_feed(body, company="Hy-Tech Engineers", now=NOW)
        self.assertEqual((len(items), count), (1, 1))
        self.assertEqual(items[0]["title"], "Hy-Tech Engineers earnings")
        self.assertEqual(items[0]["publisher"], "Publisher")
        self.assertEqual(items[0]["evidence_status"], "reported_headline_unverified")
        self.assertEqual(items[0]["excerpt"], "")
        self.assertFalse(any(skipped.values()))

    def test_old_future_missing_dates_duplicates_and_unsafe_links(self):
        recent = "Wed, 14 Oct 2026 09:00:00 GMT"
        body = rss(
            [
                ("Story", "https://publisher.example/1", recent, "Publisher"),
                ("Story", "https://publisher.example/1-copy", recent, "Publisher"),
                (
                    "Old",
                    "https://publisher.example/old",
                    "Wed, 01 Jul 2026 09:00:00 GMT",
                    "Publisher",
                ),
                (
                    "Future",
                    "https://publisher.example/future",
                    "Wed, 21 Oct 2026 09:00:00 GMT",
                    "Publisher",
                ),
                ("Undated", "https://publisher.example/no-date", "", "Publisher"),
                ("Unsafe", "javascript:alert(1)", recent, "Publisher"),
                ("Credentials", "https://user:secret@publisher.example/a", recent, "Publisher"),
            ]
        )
        items, skipped, _ = news.parse_feed(body, now=NOW)
        self.assertEqual([item["title"] for item in items], ["Story"])
        self.assertEqual(skipped["out_of_window"], 1)
        self.assertEqual(skipped["unknown_or_future_date"], 2)
        self.assertEqual(skipped["invalid_or_duplicate"], 3)

    def test_name_boundaries_legal_suffixes_and_hyphen_variants(self):
        self.assertEqual(news.name_phrase("HY-TECH ENGINEERS LIMITED"), "HY-TECH ENGINEERS")
        self.assertTrue(news.name_matches("Hytech Engineers reported results", "Hy-Tech Engineers"))
        self.assertTrue(news.name_matches("ITC announces results", "ITC"))
        self.assertFalse(news.name_matches("political commentary", "ITC"))
        self.assertFalse(news.name_matches("Another steel company", "Sambhv Steel Tubes"))

    def test_company_search_excludes_other_companies(self):
        body = rss(
            [
                (
                    "Another business results",
                    "https://publisher.example/a",
                    "Wed, 14 Oct 2026 09:00:00 GMT",
                    "Publisher",
                )
            ]
        )
        items, skipped, _ = news.parse_feed(body, company="Gem Aromatics", now=NOW)
        self.assertFalse(items)
        self.assertEqual(skipped["name_not_in_feed_text"], 1)

    def test_html_or_entity_response_is_a_failure_not_empty_news(self):
        for body in (
            b"<html><body>Sign in</body></html>",
            b"<!DOCTYPE rss><rss/>",
            b"<!ENTITY x 'text'><rss/>",
        ):
            with self.assertRaises(ValueError):
                news.parse_feed(body, now=NOW)

    def test_reddit_atom_is_unverified_and_only_accepts_reddit_links(self):
        body = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Hytech Engineers discussion</title><link href="https://www.reddit.com/r/IndianStockMarket/comments/abc/test/"/><published>2026-10-14T08:00:00Z</published><content type="html">&lt;p&gt;An opinion about the company, not a verified financial fact.&lt;/p&gt;</content></entry><entry><title>Hytech Engineers spam</title><link href="https://evil.example/a"/><published>2026-10-14T08:00:00Z</published></entry></feed>"""
        items, _, _ = news.parse_feed(body, "reddit", company="Hy-Tech Engineers", now=NOW)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["evidence_status"], "community_claim_unverified")
        self.assertNotIn("<p>", items[0]["excerpt"])

    def test_naive_date_is_not_silently_assigned_a_timezone(self):
        self.assertIsNone(news.parse_date("2026-10-14T09:00:00"))
        self.assertEqual(news.parse_date("2026-10-14T09:00:00Z").utcoffset().total_seconds(), 0)


class FeedBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.values = {}
        self.cache = patch.object(
            news,
            "cache_manager",
            SimpleNamespace(
                get=lambda key: self.values.get(key),
                set=lambda key, value, ttl: self.values.__setitem__(key, value),
            ),
        )
        self.cache.start()

    def tearDown(self):
        self.cache.stop()

    def test_cache_reuses_result_and_manual_refresh_has_cooldown(self):
        with patch.object(news, "_fetch", return_value=b"<rss><channel/></rss>") as fetch:
            first = news.feed('"cement demand"')
            second = news.feed('"cement demand"', refresh=True)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["status"], "no_matches")
        self.assertTrue(second["cached"])
        self.assertFalse(second["stale"])

    def test_failed_refresh_keeps_previous_timestamp_and_marks_stale(self):
        prior = {
            "items": [{"title": "Earlier headline"}],
            "fetched_epoch": 1000,
            "fetched_at": "old-date",
            "status": "available",
        }
        with (
            patch.object(news.cache_manager, "get", return_value=prior),
            patch.object(news.time, "time", return_value=2000),
            patch.object(news, "_fetch", side_effect=httpx.ReadTimeout("timeout")) as fetch,
        ):
            result = news.feed("query")
        self.assertTrue(result["stale"])
        self.assertEqual(result["fetched_at"], "old-date")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["items"], prior["items"])
        self.assertEqual(fetch.call_count, 1)

    def test_access_failure_is_not_no_matches_and_is_negatively_cached(self):
        with patch.object(news, "_fetch", side_effect=httpx.ReadTimeout("timeout")) as fetch:
            first = news.feed("query")
            second = news.feed("query", refresh=True)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["status"], "unavailable")
        self.assertEqual(second["status"], "unavailable")
        self.assertNotIn("query", news._active)

    def test_company_and_reddit_urls_use_fixed_hosts_and_encoded_queries(self):
        with patch.object(news, "_fetch", return_value=b"<rss><channel/></rss>") as fetch:
            news.feed('"Hy-Tech Engineers"', company="Hy-Tech Engineers")
        url = fetch.call_args.args[0]
        self.assertEqual(urlsplit(url).hostname, "news.google.com")
        self.assertIn('"Hy-Tech Engineers"', parse_qs(urlsplit(url).query)["q"][0])

    def test_unavailable_sections_do_not_produce_a_fabricated_brief(self):
        with patch.object(news, "feed", return_value={"items": [], "status": "unavailable"}):
            desk = news.reading_desk()
        self.assertFalse(desk["start_here"])
        self.assertEqual(len(desk["sections"]), 6)
        self.assertTrue(all(section["status"] == "unavailable" for section in desk["sections"]))

    def test_priority_is_explained_but_never_a_price_forecast(self):
        result = news.priority({"title": "Central bank announces interest rate decision"})
        self.assertEqual(result["reading_score"], 5)
        self.assertIn("decision", result["question"])
        self.assertNotIn("target_price", result)

    def test_community_does_not_claim_x_was_fetched(self):
        with patch.object(news, "feed", return_value={"items": [], "status": "no_matches"}) as feed:
            result = news.community({"ticker": "ACME.NS", "name": "Acme Industries Limited"})
        self.assertEqual(feed.call_count, 1)
        self.assertEqual(result["x"]["status"], "search_link_only")
        self.assertEqual(urlsplit(result["x"]["url"]).hostname, "x.com")

    def test_stock_picks_are_not_promoted_as_major_policy_news(self):
        result = news.priority(
            {
                "title": "3 Inflation Stocks Linked To Oil Prices",
                "publisher_url": "https://publisher.example",
            }
        )
        self.assertEqual(result["headline_form"], "stock_picks")
        self.assertEqual(result["reading_score"], 0)
        self.assertFalse(result["publisher_preference"])

    def test_publisher_preference_requires_matching_domain_not_just_a_name(self):
        report = news.priority(
            {
                "title": "Federal Reserve decision",
                "publisher": "Reuters",
                "publisher_url": "https://www.reuters.com/",
            }
        )
        spoof = news.priority(
            {
                "title": "Federal Reserve decision",
                "publisher": "Reuters",
                "publisher_url": "https://reuters.com.evil.example/",
            }
        )
        self.assertTrue(report["publisher_preference"])
        self.assertFalse(spoof["publisher_preference"])

    def test_start_here_chooses_reports_over_keyword_heavy_stock_tips(self):
        def result(query, **kwargs):
            base = {
                "published_at": NOW.isoformat(),
                "publisher_url": "https://www.reuters.com/",
                "publisher": query,
            }
            return {
                "status": "available",
                "items": [
                    {
                        **base,
                        "id": "tip",
                        "title": "3 Inflation Stocks Linked To Oil Prices",
                        "url": "https://example.com/tips",
                    },
                    {
                        **base,
                        "id": query,
                        "title": "Economic release: " + query,
                        "url": "https://example.com/report",
                    },
                ],
            }

        with patch.object(news, "feed", side_effect=result):
            desk = news.reading_desk()
        self.assertEqual(len(desk["start_here"]), 6)
        self.assertTrue(all(item["headline_form"] != "stock_picks" for item in desk["start_here"]))


class NewsAPITests(unittest.TestCase):
    def test_headline_relevance_not_publisher_name(self):
        self.assertFalse(
            news.headline_relevant("us", "China's Weakening Economy Is Creating a Lost Generation")
        )
        self.assertFalse(
            news.headline_relevant(
                "us", "The Mystery of the Unknown Sailor Who Inspired Trump to Shake Up the Navy"
            )
        )
        self.assertTrue(
            news.headline_relevant("us", "US stock markets slide after inflation release")
        )
        self.assertFalse(news.headline_relevant("commodities", "Celebrity visits university"))
        self.assertTrue(news.headline_relevant("commodities", "Gold prices hold firm"))

    def test_topic_validation_and_literal_query(self):
        with (
            TestClient(app) as client,
            patch(
                "routers.news.news_reader.feed", return_value={"items": [], "status": "no_matches"}
            ) as feed,
        ):
            self.assertEqual(client.get("/api/news/topic?topic=!!!").status_code, 422)
            self.assertEqual(
                client.get("/api/news/topic", params={"topic": "cement demand"}).status_code, 200
            )
        self.assertEqual(feed.call_args.args[0], '"cement demand"')

    def test_reading_desk_route_returns_partial_provider_state(self):
        with (
            TestClient(app) as client,
            patch(
                "routers.news.news_reader.reading_desk",
                return_value={"start_here": [], "sections": [{"status": "unavailable"}]},
            ),
        ):
            response = client.get("/api/news/reading-desk")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sections"][0]["status"], "unavailable")
