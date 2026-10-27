import unittest
from unittest.mock import patch

from services import research_context as context


class OfficialContextTests(unittest.TestCase):
    def test_aspnet_form_keeps_article_and_extracts_pib_date(self):
        html = (
            b'<html><body><form><input value="private-state"><div class="innner-page-main-about-us-content-right-part">Posted On: 13 OCT 2026 8:21PM '
            + b"Official heritage policy and implementation details. " * 8
            + b"</div></form></body></html>"
        )
        with (
            patch.object(context, "context_url"),
            patch.object(
                context,
                "fetch_public",
                return_value=(html, "https://www.pib.gov.in/article", "text/html"),
            ),
        ):
            article = context.read_context({"url": "https://www.pib.gov.in/article"})
        self.assertTrue(article["date"].startswith("2026-10-13T20:21"))
        self.assertNotIn("private-state", article["text"])

    def test_wrong_article_body_cannot_pass_with_correct_url(self):
        html = (
            b"<html><body><main>"
            + b"Unrelated privacy notice and website conditions. " * 10
            + b"</main></body></html>"
        )
        with (
            patch.object(context, "context_url"),
            patch.object(
                context,
                "fetch_public",
                return_value=(html, "https://www.rbi.org.in/article", "text/html"),
            ),
        ):
            with self.assertRaises(ValueError):
                context.read_context(
                    {
                        "url": "https://www.rbi.org.in/article",
                        "title": "Monetary policy repo rate decision",
                    }
                )

    def test_feeds_reject_external_links_entities_and_future_items(self):
        raw = b"<rss><channel><item><title>Current policy</title><link>https://www.pib.gov.in/a</link><pubDate>Mon, 12 Oct 2026 10:00:00 GMT</pubDate></item><item><title>Future policy</title><link>https://www.pib.gov.in/future</link><pubDate>2099-01-01</pubDate></item><item><title>External link</title><link>https://attacker.example/a</link></item></channel></rss>"
        self.assertEqual(
            [item["title"] for item in context.feed_items(raw, "feed")], ["Current policy"]
        )
        with self.assertRaises(ValueError):
            context.feed_items(b'<!DOCTYPE x [<!ENTITY e "boom">]><rss/>', "feed")

    def test_company_site_is_not_accepted_as_official_policy_source(self):
        with self.assertRaises(ValueError):
            context.context_url("https://example.com/policy")

    def test_challenge_page_never_becomes_policy_evidence(self):
        with (
            patch.object(context, "context_url"),
            patch.object(
                context,
                "fetch_public",
                return_value=(
                    b"<html><body>Access denied " + b"x" * 200 + b"</body></html>",
                    "https://www.rbi.org.in/article",
                    "text/html",
                ),
            ),
        ):
            with self.assertRaises(ValueError):
                context.read_context({"url": "https://www.rbi.org.in/article"})

    def test_html_article_has_date_and_impact_unverified_label(self):
        html = (
            b'<html><head><title>Official release</title><meta property="article:published_time" content="2026-10-12"></head><body><nav>Ignore menu</nav><main>'
            + b"Credit conditions and implementation details. " * 8
            + b"</main></body></html>"
        )
        with (
            patch.object(context, "context_url"),
            patch.object(
                context,
                "fetch_public",
                return_value=(html, "https://www.rbi.org.in/article", "text/html"),
            ),
        ):
            result = context.read_context({"url": "https://www.rbi.org.in/article"})
        self.assertEqual(result["status"], "impact_unverified")
        self.assertNotIn("Ignore menu", result["text"])
        self.assertTrue(result["date"].startswith("2026-10-12"))

    def test_no_matching_headline_is_a_gap_not_no_policy(self):
        with (
            patch.object(
                context.cache_manager,
                "get",
                return_value=[
                    {"url": "https://www.pib.gov.in/a", "title": "Workshop announced", "date": None}
                ],
            ),
            patch.object(context, "read_context") as read,
        ):
            result = context.collect_context(
                {"name": "Acme Limited", "sector": "Technology", "industry": "Software"}
            )
        read.assert_not_called()
        self.assertEqual(result["status"], "no_readable_context")

    def test_feed_outages_remain_visible_and_manual_article_is_still_tried(self):
        with (
            patch.object(context.cache_manager, "get", return_value=None),
            patch.object(context, "fetch_public", side_effect=ValueError("unavailable")),
            patch.object(context, "read_context", return_value={"id": "manual"}),
        ):
            result = context.collect_context(
                {"name": "Acme Limited"}, ["https://www.pib.gov.in/manual"]
            )
        self.assertEqual(len(result["articles"]), 1)
        self.assertTrue(all(item["status"] == "unavailable" for item in result["attempts"]))
