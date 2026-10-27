import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from services import deep_dive, supply_chain
from services.relationship_network import build_relationship_network


def profile(ticker="TCS.NS"):
    return {
        "ticker": ticker,
        "name": "Example company",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "instrument_type": "EQUITY",
        "source_url": "https://finance.yahoo.com/quote/TCS.NS/",
        "about": "Example company provides technology services to enterprise customers.",
    }


def report_payload():
    return {
        "sections": [
            {
                "id": key,
                "analysis": "Not established by supplied sources.",
                "evidence": [],
                "questions": ["What does the annual report disclose?"],
            }
            for key in deep_dive.SECTIONS
        ]
    }


class SupplyChainRestorationTests(unittest.TestCase):
    def empty_research(self):
        return {"status": "complete", "documents": [], "attempts": [], "errors": []}

    def test_known_and_unknown_companies_have_no_predefined_relationships(self):
        for ticker in ("TCS.NS", "RELIANCE.NS", "FRESHOUTSIDE.NS"):
            result = build_relationship_network(profile(ticker), self.empty_research())
            self.assertFalse(result["upstream_suppliers"])
            self.assertFalse(result["downstream_customers"])
            self.assertFalse(result["partners"])
            self.assertFalse(result["research_leads"]["upstream_suppliers"])
            self.assertTrue(result["sector_context"]["upstream_suppliers"])

    def test_collected_evidence_populates_any_company_and_preserves_partner_roles(self):
        evidence = self.empty_research()
        evidence["documents"] = [
            {
                "relationships": [
                    {
                        "id": "one",
                        "name": "Example Components",
                        "direction": "upstream_suppliers",
                        "source_page": 12,
                    },
                    {
                        "id": "two",
                        "name": "Example Research",
                        "direction": "partners",
                        "source_page": 15,
                    },
                ]
            }
        ]
        result = build_relationship_network(profile("FRESHOUTSIDE.NS"), evidence)
        self.assertEqual(result["upstream_suppliers"][0]["source_page"], 12)
        self.assertEqual(result["partners"][0]["name"], "Example Research")
        self.assertFalse(result["downstream_customers"])

    def test_duplicate_mentions_are_not_counted_as_distinct_companies(self):
        node = {"id": "one", "name": "Example", "direction": "upstream_suppliers"}
        evidence = {
            **self.empty_research(),
            "documents": [{"relationships": [node, {**node, "id": "two"}]}],
        }
        self.assertEqual(
            len(build_relationship_network(profile(), evidence)["upstream_suppliers"]), 1
        )

    def test_etf_uses_provider_holdings_instead_of_equity_network(self):
        p = {**profile("FUND.NS"), "instrument_type": "ETF"}
        frame = SimpleNamespace(
            iterrows=lambda: iter([(0, {"Name": "Holding", "Holding Percent": 0.25})])
        )
        fake = SimpleNamespace(funds_data=SimpleNamespace(top_holdings=frame))
        with (
            patch.object(supply_chain, "get_company_profile", return_value=p),
            patch.object(supply_chain.yf, "Ticker", return_value=fake),
            patch.object(supply_chain.cache_manager, "get", return_value=None),
            patch.object(supply_chain.cache_manager, "set"),
        ):
            result = supply_chain.get_company_supply_chain("FUND.NS")
        self.assertEqual(result["view_type"], "etf_holdings")
        self.assertEqual(result["holdings"][0]["weight_pct"], 25)
        self.assertNotIn("research_leads", result)


class DeepDiveRestorationTests(unittest.TestCase):
    def test_excerpt_requires_source_and_rejects_unsupported_fields(self):
        with self.assertRaises(ValidationError):
            deep_dive.DeepDiveRequest(excerpt="Filing text")
        with self.assertRaises(ValidationError):
            deep_dive.DeepDiveRequest(api_key="Do not accept client keys")

    def test_evidence_must_match_known_source_text(self):
        payload = report_payload()
        sources = [{"id": "provider", "text": profile()["about"]}]
        payload["sections"][0]["evidence"] = [
            {"source_id": "provider", "quote": "technology services to enterprise customers"}
        ]
        payload["sections"][0]["analysis"] = "technology services to enterprise customers"
        self.assertEqual(len(deep_dive._validate_report(payload, sources)["sections"]), 12)
        bad = deepcopy(payload)
        bad["sections"][0]["evidence"][0]["quote"] = "Invented market share claim"
        with self.assertRaises(ValueError):
            deep_dive._validate_report(bad, sources)
        bad = deepcopy(payload)
        bad["sections"][0]["evidence"][0]["source_id"] = "invented_source"
        with self.assertRaises(ValueError):
            deep_dive._validate_report(bad, sources)

    def test_duplicate_or_missing_sections_rejected(self):
        payload = report_payload()
        payload["sections"][-1]["id"] = "business"
        with self.assertRaises(ValueError):
            deep_dive._validate_report(payload, [])
        with self.assertRaises(ValidationError):
            deep_dive._validate_report({"sections": []}, [])

    def test_missing_credentials_are_actionable_and_never_call_provider(self):
        with (
            patch.object(deep_dive, "get_company_profile", return_value=profile()),
            patch.object(deep_dive.settings, "GEMINI_API_KEYS", ""),
            patch.object(deep_dive.httpx, "post") as post,
        ):
            with self.assertRaises(HTTPException) as caught:
                deep_dive.generate_company_deep_dive("TCS.NS", deep_dive.DeepDiveRequest())
        self.assertEqual(caught.exception.status_code, 503)
        post.assert_not_called()

    def generate(self, request, finish_reason="STOP", financials=None, provider_error=None):
        response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "candidates": [
                    {
                        "finishReason": finish_reason,
                        "content": {"parts": [{"text": json.dumps(report_payload())}]},
                    }
                ]
            },
        )
        with (
            patch.object(deep_dive, "get_company_profile", return_value=profile()),
            patch.object(deep_dive, "get_company_financials", return_value=financials or {}),
            patch.object(deep_dive, "cached_research", return_value={"documents": []}),
            patch.object(deep_dive, "filing_sources_for_ai", return_value=[]),
            patch("services.research_workflow.save_ai_relationships"),
            patch.object(deep_dive.settings, "GEMINI_API_KEYS", "test-only-key"),
            patch.object(deep_dive.gemini_rotator, "get_active_key", return_value="test-only-key"),
            patch.object(deep_dive.gemini_rotator, "report_success"),
            patch.object(deep_dive.cache_manager, "get", return_value=None),
            patch.object(deep_dive.cache_manager, "set") as save,
            patch.object(
                deep_dive.httpx, "post", return_value=response, side_effect=provider_error
            ) as post,
        ):
            result = deep_dive.generate_company_deep_dive("TCS.NS", request)
            self.assertNotIn("key=", post.call_args.args[0])
            self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-only-key")
            if financials:
                prompt = post.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
                self.assertIn("Total Assets", prompt)
                self.assertIn("2026-03-31", prompt)
            return result, save.call_count

    def test_ai_receives_period_aligned_balance_sheet_numbers_with_units(self):
        report, _ = self.generate(
            deep_dive.DeepDiveRequest(),
            financials={
                "period_dates": ["2026-03-31"],
                "balance_sheet": [{"metric": "Total Assets", "values": [100], "unit": "INR Cr"}],
            },
        )
        self.assertIn("financial_statements", [source["id"] for source in report["sources"]])

    def test_provider_only_report_cached_and_excerpts_not_persisted(self):
        report, calls = self.generate(deep_dive.DeepDiveRequest())
        self.assertEqual(calls, 1)
        self.assertNotIn("text", report["sources"][0])
        report, calls = self.generate(
            deep_dive.DeepDiveRequest(
                excerpt="Example filing text", source_url="https://example.com/filing.pdf"
            )
        )
        self.assertEqual(calls, 0)
        self.assertEqual(report["data_source"], "ai_interpretation")

    def test_partial_report_withholds_failed_sections_and_relationships(self):
        payload = report_payload()
        quote = "Example company provides technology services to enterprise customers."
        payload["sections"][0].update(
            analysis=quote, evidence=[{"source_id": "provider", "quote": quote}]
        )
        payload["sections"][1].update(
            analysis="Invented figures.",
            evidence=[{"source_id": "provider", "quote": "Unrelated unsupported claim."}],
        )
        payload["relationships"] = [
            {
                "name": "Made Up Supplier",
                "direction": "upstream_suppliers",
                "relationship": "Supplies materials",
                "source_id": "provider",
                "quote": "An invented commercial relationship.",
            }
        ]
        sources = [{"id": "provider", "text": quote, "url": "https://example.com/"}]
        result = deep_dive._validate_generated_report(payload, sources)
        self.assertEqual(result["generation_status"], "partial")
        self.assertEqual(result["sections"][0]["analysis"], quote)
        self.assertEqual(result["sections"][1]["evidence"], [])
        self.assertEqual(result["sections"][1]["analysis"], "Not established by supplied sources.")
        self.assertEqual(result["relationships"], [])
        self.assertEqual(len(result["validation_warnings"]), 2)
        with self.assertRaises(ValueError):
            deep_dive._validate_report(payload, sources)

    def test_report_with_no_surviving_evidence_or_missing_sections_still_fails(self):
        payload = report_payload()
        payload["sections"][0]["analysis"] = "An unsupported assertion."
        with self.assertRaises(ValueError):
            deep_dive._validate_generated_report(payload, [])
        payload["sections"].pop()
        with self.assertRaises(ValueError):
            deep_dive._validate_generated_report(payload, [])

    def test_provider_schema_is_simple_but_local_quote_limits_remain_strict(self):
        schema = deep_dive._provider_schema()
        self.assertEqual(schema["properties"]["sections"]["type"], "array")
        self.assertNotIn("maxLength", json.dumps(schema))
        self.assertNotIn("maxItems", json.dumps(schema))
        self.assertIn("quote", schema["$defs"]["Evidence"]["properties"])
        with self.assertRaises(ValidationError):
            deep_dive.Evidence(source_id="provider", quote="x" * 401)

    def test_live_provider_timeout_is_distinct_from_connection_failure(self):
        with self.assertRaises(HTTPException) as caught:
            self.generate(
                deep_dive.DeepDiveRequest(),
                provider_error=deep_dive.httpx.ReadTimeout("provider timeout"),
            )
        self.assertEqual(caught.exception.status_code, 504)
        self.assertIn("timed out", caught.exception.detail)

    def test_truncated_generation_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            self.generate(deep_dive.DeepDiveRequest(), finish_reason="MAX_TOKENS")
        self.assertEqual(caught.exception.status_code, 502)
