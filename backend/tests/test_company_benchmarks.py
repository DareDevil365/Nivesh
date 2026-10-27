"""Regression contracts learned from independent issuer research, using synthetic data."""

import unittest
from unittest.mock import patch

from services import (
    filing_financials,
    filing_reader,
    filing_sources,
    research_plan,
    research_workflow,
)
from tests.test_filing_workflow import make_pdf, profile


class FilingTableTests(unittest.TestCase):
    def test_first_column_integer_loss_is_not_mistaken_for_a_note(self):
        raw = self.table().replace("PAT 220 190 (110)", "PAT (220) 190 -")
        rows = filing_financials.extract_income_table(raw, self.source)
        self.assertEqual(
            [row["value_cr"] for row in rows if row["metric"] == "net_income_cr"], [-22, 19]
        )

    source = {"id": "doc:p1", "url": "https://acme.example/report.pdf", "page": 1}

    def table(self, unit="Mn", basis="Consolidated", header="FY26 FY25 FY24"):
        return f"{basis} Profit and Loss\nParticulars (Rs {unit}) {header}\nRevenue From Operations 1,890 1,610 1,370\nPAT 220 190 (110)\nPAT Margin (%) 11.6% 11.8% -8.0%"

    def test_explicit_income_table_converts_millions_and_negative_parentheses(self):
        rows = filing_financials.extract_income_table(self.table(), self.source)
        self.assertEqual([r["value_cr"] for r in rows], [189, 161, 137, 22, 19, -11])
        self.assertTrue(all(r["basis"] == "consolidated" for r in rows))

    def test_lakh_crore_and_missing_unit_are_distinct(self):
        self.assertEqual(
            filing_financials.extract_income_table(self.table("lakhs"), self.source)[0]["value_cr"],
            18.9,
        )
        self.assertEqual(
            filing_financials.extract_income_table(self.table("Cr"), self.source)[0]["value_cr"],
            1890,
        )
        self.assertFalse(filing_financials.extract_income_table(self.table("USD"), self.source))

    def test_ambiguous_basis_ranges_and_column_misalignment_are_not_parsed(self):
        for raw in (
            self.table(basis="Standalone and Consolidated"),
            self.table(header="FY2025-26 FY2024-25"),
            self.table(header="FY26 FY25"),
        ):
            with self.subTest(raw=raw):
                self.assertFalse(filing_financials.extract_income_table(raw, self.source))

    def test_notes_arithmetic_and_indian_annual_dates(self):
        text = "Standalone Statement of Proﬁt and Loss for year ended March 31, 2026\n(All amounts in Indian Rupees millions)\nParticulars Note No. For the year ended March 31, 2026 For the year ended March 31, 2025\n(a) Revenue from operations 28 24,000.00 15,000.00\nVII. Profit for the year (V - VI) 1,400.00 580.00"
        rows = filing_financials.extract_income_table(text, self.source)
        self.assertEqual(
            [(r["metric"], r["period"], r["value_cr"]) for r in rows],
            [
                ("revenue_cr", "2026-03-31", 2400),
                ("revenue_cr", "2025-03-31", 1500),
                ("net_income_cr", "2026-03-31", 140),
                ("net_income_cr", "2025-03-31", 58),
            ],
        )

    def test_cash_pat_is_not_net_income(self):
        raw = self.table().replace("PAT 220 190 (110)", "Cash PAT 220 190 110")
        rows = filing_financials.extract_income_table(raw, self.source)
        self.assertFalse(any(row["metric"] == "net_income_cr" for row in rows))

    def test_reconciliation_does_not_overwrite_unknown_basis_provider(self):
        inputs = {"period": "2026-03-31", "revenue_cr": 182, "net_income_cr": 22}
        result = filing_financials.reconcile_financials(
            inputs,
            [
                {
                    "financial_metrics": filing_financials.extract_income_table(
                        self.table(), self.source
                    )
                }
            ],
        )
        self.assertEqual(inputs["revenue_cr"], 182)
        self.assertEqual(result["comparisons"][0]["status"], "review_difference")


class DiscoveryAndScopeTests(unittest.TestCase):
    def test_html_landing_page_cannot_displace_actual_annual_report(self):
        landing = {
            "title": "Annual Reports | About Us",
            "url": "https://acme.example/annual-reports/",
            "source_kind": "company_page",
        }
        report = {"title": "Annual report 2025-2026", "url": "https://acme.example/2026.pdf"}
        self.assertEqual(filing_sources.document_kind(landing), "business")
        self.assertLess(filing_sources._priority(landing), filing_sources._priority(report))

    def test_foreign_legal_suffix_separates_two_entities(self):
        source = {
            "id": "d:p1",
            "page": 1,
            "url": "https://acme.example/report.pdf",
            "title": "Report",
        }
        nodes = filing_reader.explicit_relationships(
            "Our customers include Ventos Brasil Eireli and Anhui Spices Co. Ltd.", source
        )
        self.assertEqual(
            [n["name"] for n in nodes], ["Ventos Brasil Eireli", "Anhui Spices Co. Ltd"]
        )

    def test_and_inside_legal_name_is_not_split_into_fabricated_companies(self):
        source = {
            "id": "d:p1",
            "page": 1,
            "title": "Report",
            "url": "https://acme.example/report.pdf",
        }
        text = "Our suppliers include Alpha Power and Ispat Limited, Phil Steel and Power Private Limited and Shyam Metalics and Energy Limited."
        self.assertEqual(
            [node["name"] for node in filing_reader.explicit_relationships(text, source)],
            [
                "Alpha Power and Ispat Limited",
                "Phil Steel and Power Private Limited",
                "Shyam Metalics and Energy Limited",
            ],
        )

    def test_extensionless_document_links_and_latest_period_hint(self):
        html = (
            '<a href="/doc/4206">Concall Transcript June 2026</a><a href="/about-us">About us</a>'
        )
        links = filing_sources.document_links(html, "https://acme.example")
        self.assertEqual(len(links), 1)
        self.assertEqual(filing_sources.reporting_period_hint(links[0]), "2026-06-30")
        self.assertEqual(
            filing_sources.reporting_period_hint({"title": "Q1FY27", "url": "x"}), "2026-06-30"
        )

    def test_newspaper_pages_are_excluded_even_with_matching_issuer_cover(self):
        pdf = make_pdf(
            "Acme Industries Limited. Newspaper Publication. Our business has customers."
        )
        with patch.object(
            filing_reader,
            "fetch_public",
            return_value=(pdf, "https://acme.example/report.pdf", "application/pdf"),
        ):
            with self.assertRaisesRegex(ValueError, "unrelated third-party"):
                filing_reader.read_document(profile(), {"url": "https://acme.example/report.pdf"})

    def test_document_selection_includes_current_transcript_and_excludes_newspaper(self):
        candidates = [
            {"url": f"https://acme.example/{kind}.pdf", "title": kind}
            for kind in (
                "Annual report",
                "Prospectus",
                "Investor Presentation",
                "Financial results",
                "Call Transcript",
                "Newspaper Publication",
            )
        ]
        self.assertEqual(
            [c["title"] for c in research_workflow._select(candidates)],
            [
                "Annual report",
                "Prospectus",
                "Investor Presentation",
                "Financial results",
                "Call Transcript",
            ],
        )

    def test_customer_list_and_named_table_keep_anonymous_entities_unknown(self):
        source = {
            "id": "d:p1",
            "page": 1,
            "title": "Prospectus",
            "url": "https://acme.example/report.pdf",
        }
        text = "Our top 10 customers include Alpha (India) Limited, bōTERRA Global Limited and Brasil LTDA; other names were not disclosed."
        self.assertEqual(
            [n["name"] for n in filing_reader.explicit_relationships(text, source)],
            ["Alpha (India) Limited", "bōTERRA Global Limited", "Brasil LTDA"],
        )
        text = "Revenue from our top ten customers is presented below. Name of the Customer Fiscal 2026 Amount % 1. Example Industries Inc 176.85 9.34 2. Customer No. 2* 140.30 7.41 3. Named Hydropneumatics 116.28 6.14"
        self.assertEqual(
            [n["name"] for n in filing_reader.explicit_relationships(text, source)],
            ["Example Industries Inc", "Named Hydropneumatics"],
        )

    def test_competitor_customer_list_and_logos_do_not_establish_issuer_edges(self):
        source = {"id": "d:p1", "page": 1, "title": "Report", "url": "source"}
        for text in (
            "Our competitor customers include Alpha Limited and Bravo Limited.",
            "Customer logos: Alpha Limited, Bravo Limited.",
            "Our customers include for our Company's products.",
        ):
            self.assertFalse(filing_reader.explicit_relationships(text, source))

    def test_verified_customer_table_continues_on_next_page(self):
        source = {
            "id": "d:p2",
            "page": 2,
            "url": "https://acme.example/report.pdf",
            "title": "Prospectus",
            "continued_table_role": "customer",
        }
        text = "Name of the Customer Fiscal 2026 Amount % 5. Example USA Inc. 67.08 3.54 6. Fittings Company Inc. 63.88 3.37 7. Customer No. 7* 59.28 3.13"
        nodes = filing_reader.explicit_relationships(text, source)
        self.assertEqual(
            [node["name"] for node in nodes], ["Example USA Inc", "Fittings Company Inc"]
        )
        self.assertTrue(all("Name of the Customer" in node["evidence_quote"] for node in nodes))

    def test_reported_company_html_can_establish_suppliers_without_pdf_page(self):
        html = (
            b"<html><title>Acme Industries Limited</title><body><main>The company is Acme Industries Limited. Our key raw material suppliers such as Alpha and BRAVO provide supply. "
            + b"Our business manufactures industrial products. " * 5
            + b"</main></body></html>"
        )
        document = filing_reader.read_company_page(
            profile(), {}, html, "https://acme.example/our-organization"
        )
        self.assertEqual([n["name"] for n in document["relationships"]], ["Alpha", "BRAVO"])
        self.assertTrue(all(n["source_page"] is None for n in document["relationships"]))

    def test_industry_plans_are_questions_not_company_answer_maps(self):
        for industry, expected in (
            ("Steel", "steel"),
            ("Chemicals", "chemicals"),
            ("Hydraulic machinery", "precision_manufacturing"),
        ):
            plan = research_plan.build_research_plan({"industry": industry}, [])
            self.assertEqual(plan["business_template"], expected)
            self.assertTrue(all(check["status"] == "missing_evidence" for check in plan["checks"]))
