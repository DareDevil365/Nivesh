import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from services import deep_dive, filing_reader, filing_sources, local_store, research_workflow


def profile():
    return {
        "ticker": "FRESHOUTSIDE.NS",
        "name": "Acme Industries Limited",
        "website": "https://acme.example",
        "sector": "Industrials",
    }


def make_pdf(text):
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream.set_data(f"BT /F1 12 Tf 20 760 Td ({escaped}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class FilingSourceTests(unittest.TestCase):
    def test_allowlist_rejects_fake_official_hosts_and_credentials(self):
        self.assertFalse(
            filing_sources.allowed_host("nseindia.com.attacker.example", "https://acme.example")
        )
        for url in (
            "http://www.nseindia.com/a.pdf",
            "https://user:pass@www.nseindia.com/a.pdf",
            "https://www.nseindia.com:8443/a.pdf",
            "https://other.example/a.pdf",
        ):
            with self.assertRaises(ValueError):
                filing_sources.validate_source_url(url, "https://acme.example")

    def test_private_dns_address_rejected(self):
        with patch.object(
            filing_sources.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]
        ):
            with self.assertRaises(ValueError):
                filing_sources.validate_source_url("https://www.nseindia.com/a.pdf", "")

    def test_redirect_target_is_validated_and_streamed_limit_enforced(self):
        original = httpx.Client
        for response in (
            httpx.Response(302, headers={"location": "https://127.0.0.1/private"}),
            httpx.Response(200, content=b"x" * 100),
        ):
            client = original(transport=httpx.MockTransport(lambda request, r=response: r))
            with (
                patch.object(filing_sources.httpx, "Client", return_value=client),
                patch.object(
                    filing_sources.socket,
                    "getaddrinfo",
                    return_value=[(2, 1, 6, "", ("8.8.8.8", 443))],
                ),
            ):
                with self.assertRaises(ValueError):
                    filing_sources.fetch_public(
                        "https://www.nseindia.com/source.pdf", "", max_bytes=10
                    )

    def test_html_pdf_zip_and_viewer_links_discovered(self):
        html = '<a href="report.pdf">Annual report</a><a href="archive.zip">Prospectus</a><iframe src="/web/?file=https://www.sebi.gov.in/report.pdf"></iframe>'
        links = filing_sources.document_links(html, "https://acme.example/investor/")
        self.assertIn("https://acme.example/investor/report.pdf", [link["url"] for link in links])
        self.assertIn("https://www.sebi.gov.in/report.pdf", [link["url"] for link in links])

    def test_discovery_uses_requested_symbol_in_live_adapter_without_company_catalog(self):
        paths = []

        def fetch(url, website, max_bytes):
            paths.append(url)
            if "annual-reports" in url:
                data = {
                    "data": [
                        {
                            "fileName": "https://nsearchives.nseindia.com/annual.pdf",
                            "fromYr": "2025",
                            "toYr": "2026",
                        }
                    ]
                }
            elif "ipo-detail" in url:
                data = {
                    "issueInfo": {
                        "dataList": [
                            {
                                "title": "Red Herring Prospectus",
                                "value": "https://nsearchives.nseindia.com/issuer.zip",
                            }
                        ]
                    }
                }
            else:
                data = []
            return json.dumps(data).encode(), url, "application/json"

        with patch.object(filing_sources, "fetch_public", side_effect=fetch):
            candidates, _ = filing_sources.discover_documents({**profile(), "website": ""})
        self.assertTrue(all("FRESHOUTSIDE" in url for url in paths))
        self.assertEqual(len(candidates), 2)


class FilingReaderTests(unittest.TestCase):
    def test_defined_short_alias_with_space_merges_duplicate_supplier_partner(self):
        pdf = make_pdf(
            'Acme Industries Limited. Beta Components Limited (" Beta") is our supplier. Beta Components Limited pursuant to the manufacture and supply agreement. We have a partnership with Beta.'
        )
        with patch.object(
            filing_reader,
            "fetch_public",
            return_value=(pdf, "https://acme.example/report.pdf", "application/pdf"),
        ):
            document = filing_reader.read_document(
                profile(), {"url": "https://acme.example/report.pdf", "title": "Report"}
            )
        self.assertEqual(
            [(node["name"], node["direction"]) for node in document["relationships"]],
            [("Beta Components Limited", "upstream_suppliers")],
        )

    def test_issuer_exchange_abbreviation_is_not_its_own_partner(self):
        pdf = make_pdf(
            "Acme Industries Limited. We announced a partnership with FRESHOUTSIDE, expanding services."
        )
        with patch.object(
            filing_reader,
            "fetch_public",
            return_value=(pdf, "https://acme.example/report.pdf", "application/pdf"),
        ):
            document = filing_reader.read_document(
                profile(), {"url": "https://acme.example/report.pdf", "title": "Report"}
            )
        self.assertFalse(document["relationships"])

    def test_pdf_and_zip_have_page_citations_and_explicit_supplier(self):
        pdf = make_pdf(
            "Acme Industries Limited. Beta Components Limited pursuant to the manufacture and supply agreement. Our suppliers manufacture products."
        )
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as writer:
            writer.writestr("../../report.pdf", pdf)
        for content in (pdf, archive.getvalue()):
            with patch.object(
                filing_reader,
                "fetch_public",
                return_value=(content, "https://acme.example/report.pdf", "application/pdf"),
            ):
                document = filing_reader.read_document(
                    profile(), {"url": "https://acme.example/report.pdf", "title": "Annual report"}
                )
            self.assertEqual(document["pages_read"], 1)
            supplier = document["relationships"][0]
            self.assertEqual(supplier["name"], "Beta Components Limited")
            self.assertEqual(supplier["source_page"], 1)
            self.assertIn("manufacture and supply", supplier["evidence_quote"])

    def test_unrelated_issuer_report_is_rejected(self):
        with patch.object(
            filing_reader,
            "fetch_public",
            return_value=(
                make_pdf("Other Business Limited. Our suppliers manufacture products."),
                "https://acme.example/report.pdf",
                "application/pdf",
            ),
        ):
            with self.assertRaises(ValueError):
                filing_reader.read_document(profile(), {"url": "https://acme.example/report.pdf"})

    def test_competitor_and_related_party_mentions_do_not_create_supplier(self):
        source = {
            "id": "doc:p1",
            "url": "https://acme.example/report.pdf",
            "title": "Report",
            "page": 1,
        }
        text = "Our competitor Beta Components Limited has expanded. Our related party Gamma Limited is an associate."
        self.assertEqual(filing_reader.explicit_relationships(text, source), [])

    def test_sourcing_brands_are_labelled_as_brands_not_legal_counterparties(self):
        source = {
            "id": "doc:p1",
            "url": "https://acme.example/report.pdf",
            "title": "Report",
            "page": 1,
        }
        text = "Our procurement process involves sourcing products from established brands including Alpha, Bravo and Charlie as well as our own private-label brands."
        nodes = filing_reader.explicit_relationships(text, source)
        self.assertEqual([node["name"] for node in nodes], ["Alpha", "Bravo", "Charlie"])
        self.assertTrue(all(node["category"] == "Disclosed sourcing brand" for node in nodes))

    def test_unsupported_archive_and_wrong_identity_fail_closed(self):
        with self.assertRaises(ValueError):
            filing_reader._pdfs(b"not a report")
        self.assertFalse(filing_reader.identity_matches(profile(), "Other Industries Limited"))


class ResearchWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.storage = patch.object(local_store, "DATA_DIR", Path(self.directory.name))
        self.storage.start()
        self.context = patch.object(
            research_workflow,
            "collect_context",
            return_value={"articles": [], "status": "no_readable_context"},
        )
        self.context.start()

    def tearDown(self):
        self.context.stop()
        self.storage.stop()
        self.directory.cleanup()

    def test_read_source_results_persist_and_failures_remain_visible(self):
        candidate = {"url": "https://acme.example/report.pdf", "title": "Annual report"}
        document = {
            "id": "content-id",
            "url": candidate["url"],
            "title": candidate["title"],
            "relationships": [],
            "passages": [],
        }
        payload = {
            "ticker": profile()["ticker"],
            "status": "queued",
            "documents": [],
            "attempts": [],
            "errors": [],
        }
        with (
            patch.object(
                research_workflow,
                "discover_documents",
                return_value=([candidate], [{"source": "NSE", "status": "checked"}]),
            ),
            patch.object(research_workflow, "read_document", return_value=document),
            patch.object(research_workflow, "get_company_financials", return_value={}),
        ):
            research_workflow._run(profile(), [], payload)
        state = research_workflow.cached_research(profile()["ticker"])
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["documents"][0]["id"], "content-id")
        with (
            patch.object(research_workflow, "discover_documents", return_value=([candidate], [])),
            patch.object(
                research_workflow, "read_document", side_effect=ValueError("Scanned PDF needs OCR")
            ),
            patch.object(research_workflow, "get_company_financials", return_value={}),
        ):
            research_workflow._run(profile(), [], {**payload, "documents": []})
        state = research_workflow.cached_research(profile()["ticker"])
        self.assertEqual(state["status"], "complete_with_gaps")
        self.assertIn("OCR", state["errors"][0]["message"])

    def test_cache_reused_and_interrupted_process_can_be_retried(self):
        research_workflow._write(profile()["ticker"], {"status": "running", "documents": []})
        self.assertEqual(
            research_workflow.cached_research(profile()["ticker"])["status"], "interrupted"
        )

    def test_ai_sources_have_bounded_text_and_page_references(self):
        passage = {"id": "doc:p1:business", "page": 1, "score": 1, "text": "a" * 40000}
        research_workflow._write(
            profile()["ticker"],
            {
                "status": "complete",
                "documents": [
                    {
                        "id": "doc",
                        "url": "https://acme.example/report.pdf",
                        "title": "Report",
                        "passages": [passage],
                        "relationships": [],
                    }
                ],
            },
        )
        sources = research_workflow.filing_sources_for_ai(profile()["ticker"])
        self.assertEqual(len(sources[0]["text"]), 28000)
        self.assertEqual(sources[0]["page"], 1)

    def test_ai_relationship_must_cite_entity_and_role_language(self):
        payload = {
            "sections": [
                {
                    "id": key,
                    "analysis": "Not established by supplied sources.",
                    "evidence": [],
                    "questions": [],
                }
                for key in deep_dive.SECTIONS
            ],
            "relationships": [
                {
                    "name": "Beta",
                    "direction": "upstream_suppliers",
                    "relationship": "Supplies products",
                    "source_id": "doc:p1",
                    "quote": "We purchase products from Beta.",
                }
            ],
        }
        sources = [
            {
                "id": "doc:p1",
                "title": "Report",
                "url": "https://acme.example/report.pdf",
                "page": 1,
                "text": "We purchase products from Beta.",
            }
        ]
        self.assertEqual(
            deep_dive._validate_report(payload, sources)["relationships"][0]["source_page"], 1
        )
        payload["relationships"][0]["name"] = "Invented"
        with self.assertRaises(ValueError):
            deep_dive._validate_report(payload, sources)
