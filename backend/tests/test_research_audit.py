import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services import (
    deep_dive,
    filing_reader,
    filing_sources,
    local_store,
    research_audit,
    research_workflow,
)
from tests.test_filing_workflow import make_pdf, profile


class DataAuditTests(unittest.TestCase):
    def test_actual_report_outranks_meeting_and_results_notice(self):
        annual = {"url": "https://acme.example/report.pdf", "title": "Annual report 2025-2026"}
        meeting = {
            "url": "https://acme.example/meeting.pdf",
            "title": "Proceedings of Annual General Meeting",
        }
        notice = {
            "url": "https://acme.example/notice.pdf",
            "title": "Date of Board Meeting for the Financial Results for Q2FY27",
        }
        results = {
            "url": "https://acme.example/results.pdf",
            "title": "Financial results for period ended June 2026",
        }
        presentation = {
            "url": "https://acme.example/presentation.pdf",
            "title": "Investor presentation",
        }
        self.assertGreater(filing_sources._priority(annual), filing_sources._priority(meeting))
        self.assertEqual(
            research_workflow._select([annual, results, presentation, meeting, notice]),
            [annual, results, presentation],
        )

    def test_incorrect_units_nonfinite_values_and_misaligned_periods_are_failures(self):
        financials = {
            "period_dates": ["2026-03-31"],
            "income_statement": [
                {"metric": "Diluted EPS", "values": [12], "unit": "₹ Cr"},
                {"metric": "Total Revenue", "values": [float("inf")], "unit": "₹ Cr"},
                {"metric": "Net Income", "values": [1, 2], "unit": "₹ Cr"},
            ],
        }
        result = research_audit.audit_research({"documents": []}, financials)
        self.assertEqual(sum(check["status"] == "fail" for check in result["checks"]), 3)

    def test_future_and_duplicate_periods_fail(self):
        for periods in (["2099-03-31"], ["2025-03-31", "2025-03-31"], ["2026-03-31", "2025-03-31"]):
            with self.subTest(periods=periods):
                result = research_audit.audit_research({"documents": []}, {"period_dates": periods})
                self.assertEqual(
                    next(
                        c["status"] for c in result["checks"] if c["check"] == "statement_periods"
                    ),
                    "fail",
                )

    def test_restatement_is_flagged_for_review_and_missing_input_is_not_zero(self):
        state = {"documents": [], "financial_inputs": {"period": "2026-03-31", "revenue_cr": 100}}
        result = research_audit.audit_research(
            state,
            {
                "period_dates": ["2026-03-31"],
                "income_statement": [{"metric": "Total Revenue", "values": [120], "unit": "₹ Cr"}],
            },
        )
        self.assertEqual(
            next(
                c["status"]
                for c in result["checks"]
                if c["check"] == "baseline_comparison:revenue_cr"
            ),
            "warning",
        )
        self.assertEqual(
            next(c["status"] for c in result["checks"] if c["check"] == "input:net_income_cr"),
            "warning",
        )

    def test_original_page_quote_is_checked_against_redownloaded_pdf(self):
        pdf = make_pdf("Acme Industries Limited. We purchase products from Beta.")
        doc = {
            "id": hashlib.sha256(pdf).hexdigest()[:20],
            "url": "https://acme.example/report.pdf",
            "relationships": [
                {
                    "name": "Beta",
                    "source_page": 1,
                    "evidence_quote": "We purchase products from Beta.",
                }
            ],
        }
        with patch.object(
            research_audit, "fetch_public", return_value=(pdf, doc["url"], "application/pdf")
        ):
            self.assertTrue(
                all(
                    check["status"] == "pass"
                    for check in research_audit.verify_originals(profile(), {"documents": [doc]})
                )
            )
            doc["relationships"][0]["evidence_quote"] = "We purchase products from Invented."
            self.assertEqual(
                research_audit.verify_originals(profile(), {"documents": [doc]})[0]["status"],
                "fail",
            )

    def test_numerical_unit_reinterpretation_is_rejected(self):
        quote = "Revenue was 80 lakh rupees."
        payload = {
            "sections": [
                {"id": key, "analysis": "Not established by supplied sources."}
                for key in deep_dive.SECTIONS
            ]
        }
        payload["sections"][0].update(
            analysis=quote,
            evidence=[{"source_id": "doc", "quote": quote}],
            interpretation="Revenue of 80 crore implies a strong position.",
        )
        with self.assertRaises(ValueError):
            deep_dive._validate_report(payload, [{"id": "doc", "text": quote}])

    def test_opposite_direction_and_external_context_cannot_create_ai_supplier(self):
        for quote, kind in (
            ("We supply products to Beta.", "issuer"),
            ("We purchase products from Beta.", "external_context"),
        ):
            payload = {
                "sections": [
                    {"id": key, "analysis": "Not established by supplied sources."}
                    for key in deep_dive.SECTIONS
                ],
                "relationships": [
                    {
                        "name": "Beta",
                        "direction": "upstream_suppliers",
                        "relationship": "Supplies products",
                        "source_id": "doc",
                        "quote": quote,
                    }
                ],
            }
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                deep_dive._validate_report(
                    payload, [{"id": "doc", "text": quote, "source_kind": kind}]
                )

    def test_short_page_preserves_all_matched_evidence_categories(self):
        pdf = make_pdf(
            "Acme Industries Limited. Our business faces competition and interest rate risk. Our suppliers impact working capital and demand."
        )
        with patch.object(
            filing_reader,
            "fetch_public",
            return_value=(pdf, "https://acme.example/report.pdf", "application/pdf"),
        ):
            doc = filing_reader.read_document(profile(), {"url": "https://acme.example/report.pdf"})
        self.assertTrue(
            {"business", "supply_chain", "risks", "policy", "financials", "demand"}
            <= {p["category"] for p in doc["passages"]}
        )

    def test_exchange_returned_wrong_symbol_is_not_attached(self):
        with patch.object(
            filing_sources,
            "fetch_public",
            return_value=(
                b'{"data":[{"symbol":"WRONG","fileName":"https://nsearchives.nseindia.com/wrong.pdf"}]}',
                "source",
                "application/json",
            ),
        ):
            candidates, attempts = filing_sources.discover_documents({**profile(), "website": ""})
        self.assertFalse(candidates)
        self.assertTrue(any(attempt["status"] == "rejected" for attempt in attempts))

    def test_company_hostname_cannot_widen_to_all_com(self):
        self.assertFalse(filing_sources.allowed_host("attacker.com", "https://com"))


class EvidenceVersionTests(unittest.TestCase):
    def test_late_ai_write_cannot_overwrite_new_collection(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(local_store, "DATA_DIR", Path(directory)),
        ):
            old = {
                "status": "complete",
                "documents": [{"id": "old", "passages": [], "relationships": []}],
            }
            new = {
                "status": "complete",
                "documents": [{"id": "new", "passages": [], "relationships": []}],
            }
            research_workflow._write("ACME.NS", new)
            research_workflow.save_ai_relationships(
                "ACME.NS", [{"name": "stale"}], research_workflow.corpus_fingerprint(old)
            )
            self.assertNotIn("ai_relationships", research_workflow._read("ACME.NS"))
            research_workflow.save_ai_relationships(
                "ACME.NS", [], research_workflow.corpus_fingerprint(new)
            )
            self.assertIn("ai_relationships", research_workflow._read("ACME.NS"))

    def test_extraction_text_and_context_changes_invalidate_corpus(self):
        first = {"documents": [{"id": "same-pdf", "extraction_version": 1, "passages": []}]}
        second = {"documents": [{"id": "same-pdf", "extraction_version": 2, "passages": []}]}
        third = {**second, "context": {"articles": [{"id": "policy"}]}}
        self.assertEqual(
            len({research_workflow.corpus_fingerprint(s) for s in (first, second, third)}), 3
        )
