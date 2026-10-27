import copy
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services import news_digest as digest


def fixture():
    source = {
        "id": "abc",
        "title": "US inflation falls to 3 percent",
        "url": "https://example.com/report",
        "publisher": "Example",
        "published_at": "2026-10-14T00:00:00+00:00",
        "read_status": "headline_only",
        "categories": ["us"],
        "evidence_text": "",
    }
    pack = {
        "date_ist": "2026-10-14",
        "generated_at": "2026-10-14T00:30:00+00:00",
        "items": [source],
        "coverage": {"headlines": 1, "headline_only": 1, "feed_excerpts": 0, "article_excerpts": 0},
        "feeds": [],
        "limitations": "Fixture",
    }
    summary = {
        "reviewed_ids": ["abc"],
        "sections": [
            {
                "category": "us",
                "bullets": [
                    {
                        "text": "A reported US headline says inflation fell to 3 percent.",
                        "why_it_matters": "Lower inflation could affect rate expectations; check the official release.",
                        "support": [{"source_id": "abc", "quote": source["title"]}],
                    }
                ],
            }
        ],
    }
    return pack, summary


class DigestTests(unittest.TestCase):
    def test_plain_text_preserves_summary_sources_dates_and_labels(self):
        pack, summary = fixture()
        saved = digest.validate_summary(pack, summary)
        rendered = digest.email_text(saved)
        self.assertIn(saved["sections"][0]["bullets"][0]["text"], rendered)
        self.assertIn("https://example.com/report", rendered)
        self.assertIn("2026-10-14", rendered)
        self.assertIn("headline only", rendered)
        self.assertIn("Why it may matter:", rendered)
        self.assertNotIn("<html>", rendered)

    def test_plain_text_rejects_unsafe_citation_links(self):
        pack, summary = fixture()
        saved = digest.validate_summary(pack, summary)
        saved["sections"][0]["bullets"][0]["sources"][0]["url"] = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            digest.email_text(saved)

    def test_delivery_claim_is_exclusive(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(digest, "DIGEST_DIR", Path(folder)),
        ):
            digest.claim_delivery("2026-10-14")
            with self.assertRaises(FileExistsError):
                digest.claim_delivery("2026-10-14")

    def test_india_day_boundary(self):
        self.assertEqual(
            digest.local_day(datetime(2026, 10, 13, 20, tzinfo=timezone.utc)), "2026-10-14"
        )

    def test_valid_summary_and_actual_coverage_label(self):
        pack, summary = fixture()
        result = digest.validate_summary(pack, summary)
        rendered = digest.email_html(result)
        self.assertIn("headline only", rendered)
        self.assertIn("3 percent", rendered)
        self.assertEqual(
            result["sections"][0]["bullets"][0]["sources"][0]["read_status"], "headline_only"
        )

    def test_unknown_sources_quotes_numbers_categories_and_review_gaps_fail(self):
        for case in (
            "source",
            "quote",
            "number",
            "category",
            "missing_review",
            "duplicate_review",
            "duplicate_section",
        ):
            pack, summary = fixture()
            bullet = summary["sections"][0]["bullets"][0]
            if case == "source":
                bullet["support"][0]["source_id"] = "missing"
            if case == "quote":
                bullet["support"][0]["quote"] = "Invented supporting quotation"
            if case == "number":
                bullet["text"] = "Inflation was 9 percent, according to the source."
            if case == "category":
                summary["sections"][0]["category"] = "india"
            if case == "missing_review":
                summary["reviewed_ids"] = []
            if case == "duplicate_review":
                summary["reviewed_ids"] = ["abc", "abc"]
            if case == "duplicate_section":
                summary["sections"].append(copy.deepcopy(summary["sections"][0]))
            with self.subTest(case=case), self.assertRaises(ValueError):
                digest.validate_summary(pack, summary)

    def test_email_escapes_untrusted_text_and_rejects_unsafe_links(self):
        pack, summary = fixture()
        summary["sections"][0]["bullets"][0]["text"] += " <script>alert('x')</script>"
        result = digest.validate_summary(pack, summary)
        self.assertNotIn("<script>", digest.email_html(result))
        result["sections"][0]["bullets"][0]["sources"][0]["url"] = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            digest.email_html(result)

    def test_article_rejects_wrong_heading_paywall_and_access_challenge(self):
        text = "A detailed economic explanation with public evidence. " * 30
        valid = f"<article><h1>US inflation falls</h1><p>{text}</p></article>".encode()
        self.assertGreater(len(digest.article_text(valid, "US inflation falls")), 600)
        for raw in (
            valid.replace(b"US inflation falls", b"Football match results"),
            valid + b'<script type="application/ld+json">{"isAccessibleForFree":false}</script>',
            b"<h1>US inflation falls</h1><article><p>Verify you are human</p></article>",
        ):
            with self.assertRaises(ValueError):
                digest.article_text(raw, "US inflation falls")

    def test_collection_deduplicates_titles_and_filters_24_hour_window(self):
        source = fixture()[0]["items"][0]
        desk = {
            "sections": [
                {
                    "id": "us",
                    "status": "available",
                    "items": [
                        source,
                        {
                            **source,
                            "id": "old",
                            "title": "Old story",
                            "published_at": "2026-10-10T00:00:00Z",
                        },
                    ],
                }
            ]
        }
        with (
            patch.object(digest.news_reader, "reading_desk", return_value=desk),
            patch.object(
                digest.news_reader, "feed", return_value={"status": "available", "items": []}
            ),
            patch.object(
                digest,
                "direct_feed",
                return_value={
                    "id": "mock",
                    "status": "available",
                    "items": [
                        {
                            **source,
                            "category": "world",
                            "evidence_text": "Publisher feed excerpt",
                            "read_status": "publisher_feed_excerpt",
                        }
                    ],
                },
            ),
        ):
            result = digest.collect(
                datetime(2026, 10, 14, 1, tzinfo=timezone.utc), read_articles=False
            )
        self.assertEqual(result["coverage"]["headlines"], 1)
        self.assertEqual(result["items"][0]["categories"], ["us", "world"])
        self.assertEqual(result["coverage"]["feed_excerpts"], 1)

    def test_archive_and_latest_route_no_email_identity(self):
        pack, summary = fixture()
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(digest, "DIGEST_DIR", Path(folder)),
        ):
            self.assertIsNone(digest.latest())
            saved = digest.validate_summary(pack, summary)
            digest.atomic_json(Path(folder) / "2026-10-14-digest.json", saved)
            with TestClient(app) as client:
                response = client.get("/api/news/digest/latest")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["digest"]["date_ist"], "2026-10-14")
            self.assertNotIn("message_id", response.text)


if __name__ == "__main__":
    unittest.main()
