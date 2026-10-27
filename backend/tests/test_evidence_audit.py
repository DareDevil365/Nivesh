"""Adversarial cases: plausible wording must not turn into unsupported research facts."""

import io
import unittest
import zipfile
from unittest.mock import patch

from services import deep_dive, filing_reader, research_workflow
from tests import test_filing_workflow as fixtures

make_pdf, profile = fixtures.make_pdf, fixtures.profile


class RelationshipAuditTests(unittest.TestCase):
    source = {
        "id": "doc:p1",
        "page": 1,
        "title": "Report",
        "url": "https://acme.example/report.pdf",
        "issuer_terms": ["ACME"],
    }

    def test_negative_proposed_ended_and_third_party_edges_are_not_facts(self):
        cases = [
            "We have no partnership with Beta Cloud.",
            "We are considering a partnership with Beta Cloud.",
            "We terminated our partnership with Beta Cloud.",
            "Our business grew. Other Business announced a partnership with Beta Cloud.",
            "Our competitor announced a partnership with Beta Cloud.",
            "Our parent company announced a partnership with Beta Cloud.",
            "We do not sell products to households.",
            "Our competitor sells products to households.",
            "We have stopped sourcing products from brands including Alpha and Bravo.",
            "Our competitors purchase products from brands including Alpha and Bravo.",
            "Our products are not manufactured in partnership with Beta Components Limited.",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(filing_reader.explicit_relationships(text, self.source), [])

    def test_issuer_mentioned_as_object_does_not_own_competitors_partner(self):
        text = "Other Business, a competitor of ACME, announced a partnership with Beta Cloud."
        self.assertEqual(filing_reader.explicit_relationships(text, self.source), [])

    def test_shared_name_tokens_are_not_document_identity(self):
        self.assertFalse(
            filing_reader.identity_matches(
                profile(), "Acme Components Limited. Industries outlook."
            )
        )

    def test_archive_tries_matching_report_instead_of_largest_unrelated_pdf(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as writer:
            writer.writestr(
                "unrelated.pdf", make_pdf("Other Business Limited. " + "Our business. " * 80)
            )
            writer.writestr(
                "issuer.pdf", make_pdf("Acme Industries Limited. Our business provides services.")
            )
        with patch.object(
            filing_reader,
            "fetch_public",
            return_value=(archive.getvalue(), self.source["url"], "application/zip"),
        ):
            document = filing_reader.read_document(profile(), {"url": self.source["url"]})
        self.assertEqual(document["archive_member"], "issuer.pdf")


class AIClaimAuditTests(unittest.TestCase):
    def test_qualitative_hypothesis_is_separate_from_quoted_facts(self):
        payload = self.payload()
        quote = "We provide services to businesses."
        payload["sections"][0].update(
            analysis=quote,
            evidence=[{"source_id": "doc", "quote": quote}],
            interpretation="If customer investment weakens, demand could soften; test this against order disclosures.",
        )
        result = deep_dive._validate_report(payload, [{"id": "doc", "text": quote}])
        self.assertEqual(result["sections"][0]["analysis"], quote)
        self.assertIn("could soften", result["sections"][0]["interpretation"])
        self.assertEqual(result["sections"][0]["verification"], "quoted_evidence")

    def payload(self):
        return {
            "sections": [
                {
                    "id": key,
                    "analysis": "Not established by supplied sources.",
                    "evidence": [],
                    "questions": [],
                }
                for key in deep_dive.SECTIONS
            ]
        }

    def test_factual_prose_without_evidence_is_rejected(self):
        payload = self.payload()
        payload["sections"][0]["analysis"] = (
            "The company is the market leader and revenue will triple."
        )
        with self.assertRaises(ValueError):
            deep_dive._validate_report(payload, [])

    def test_real_quote_cannot_launder_invented_analysis(self):
        payload = self.payload()
        payload["sections"][0].update(
            analysis="Revenue rose 80% and margins will double.",
            evidence=[{"source_id": "doc", "quote": "We provide services to businesses."}],
        )
        with self.assertRaises(ValueError):
            deep_dive._validate_report(
                payload, [{"id": "doc", "text": "We provide services to businesses."}]
            )

    def test_ai_negated_relationship_is_rejected_even_with_exact_quote(self):
        for quote in (
            "We have no partnership with Beta Cloud.",
            "Our competitor has a partnership with Beta Cloud.",
        ):
            payload = self.payload()
            payload["relationships"] = [
                {
                    "name": "Beta Cloud",
                    "direction": "partners",
                    "relationship": "Strategic partnership",
                    "source_id": "doc",
                    "quote": quote,
                }
            ]
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                deep_dive._validate_report(
                    payload,
                    [
                        {
                            "id": "doc",
                            "text": quote,
                            "url": "https://acme.example/report.pdf",
                            "title": "Report",
                        }
                    ],
                )


class RefreshAuditTests(unittest.TestCase):
    setUp = fixtures.ResearchWorkflowTests.setUp
    tearDown = fixtures.ResearchWorkflowTests.tearDown

    def test_failed_refresh_never_relabels_old_documents_as_current(self):
        old = {"id": "old", "passages": [], "relationships": []}
        payload = {"status": "queued", "documents": [old], "errors": []}
        with (
            patch.object(research_workflow, "discover_documents", return_value=([], [])),
            patch.object(research_workflow, "get_company_financials", return_value={}),
        ):
            research_workflow._run(profile(), [], payload)
        state = research_workflow.cached_research(profile()["ticker"])
        self.assertEqual(state["documents"], [])
        self.assertEqual(state["previous_documents"], [old])

    def test_collection_tries_alternates_when_top_candidates_fail(self):
        candidates = [
            {"url": f"https://acme.example/{i}.pdf", "title": f"Report {i}"} for i in range(4)
        ]
        document = {"id": "valid", "passages": [], "relationships": []}
        with (
            patch.object(research_workflow, "discover_documents", return_value=(candidates, [])),
            patch.object(
                research_workflow,
                "read_document",
                side_effect=[ValueError("wrong issuer")] * 3 + [document],
            ),
            patch.object(research_workflow, "get_company_financials", return_value={}),
        ):
            research_workflow._run(
                profile(), [], {"status": "queued", "documents": [], "errors": []}
            )
        self.assertEqual(
            research_workflow.cached_research(profile()["ticker"])["documents"], [document]
        )

    def test_submit_failure_releases_queue_slot(self):
        with patch.object(
            research_workflow._pool, "submit", side_effect=RuntimeError("executor stopped")
        ):
            with self.assertRaises(RuntimeError):
                research_workflow.start_research(profile())
        self.assertNotIn(profile()["ticker"], research_workflow._active)
