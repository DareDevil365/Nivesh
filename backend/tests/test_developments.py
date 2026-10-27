import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from services import company_events as events
from services import local_store, research_workflow
from tests.test_filing_workflow import make_pdf, profile


class DevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.storage = patch.object(local_store, "DATA_DIR", Path(self.directory.name))
        self.storage.start()

    def tearDown(self):
        self.storage.stop()
        self.directory.cleanup()

    def state(self):
        return {
            "status": "complete",
            "documents": [],
            "candidates": [
                {
                    "title": "Clarification on media reports",
                    "url": "https://acme.example/clarification.pdf",
                    "date": "2025-05-01",
                },
                {
                    "title": "Order received",
                    "url": "https://acme.example/order.pdf",
                    "date": "2025-05-02",
                },
                {
                    "title": "Newspaper publication",
                    "url": "https://acme.example/paper.pdf",
                    "date": "2025-05-03",
                },
            ],
        }

    def test_headline_is_not_project_outcome_or_verified_rumour(self):
        result = events.developments("ACME.NS", self.state())
        self.assertEqual(len(result["items"]), 2)
        self.assertTrue(all(item["evidence_status"] == "headline_lead" for item in result["items"]))
        self.assertTrue(all("stage" not in item for item in result["items"]))
        self.assertFalse(result["follow_up_leads"])

    def test_takeover_regulation_reference_is_not_an_acquisition(self):
        self.assertEqual(
            events.event_kind(
                "Disclosure under Substantial Acquisition of Shares and Takeovers Regulations"
            ),
            "ownership",
        )
        self.assertEqual(
            events.event_kind(
                "Appointment of Monitoring Agency for Preferential Issue of Warrants"
            ),
            "financing",
        )

    def test_idempotent_history_preserves_source_versions_and_current_scope(self):
        state = self.state()
        first = events.developments("ACME.NS", state)
        second = events.developments("ACME.NS", state)
        self.assertEqual(first["items"], second["items"])
        doc = {
            "id": "v1",
            "title": "Order received",
            "url": state["candidates"][1]["url"],
            "date": "2025-05-02",
            "passages": [{"id": "v1:p1", "text": "We did not win the tender.", "page": 1}],
        }
        state["documents"] = [doc]
        result = events.developments("ACME.NS", state)
        item = next(item for item in result["items"] if item["kind"] == "project")
        self.assertEqual(item["evidence_status"], "document_excerpt")
        self.assertEqual(item["evidence"][0]["text"], "We did not win the tender.")
        self.assertNotIn("stage", item)
        self.assertTrue(item["in_current_collection"])
        stale = events.developments("ACME.NS", {"documents": [], "candidates": []})
        self.assertFalse(any(item["in_current_collection"] for item in stale["items"]))
        with local_store.connection() as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM development_observations").fetchone()[0], 3
            )

    def test_future_and_unsafe_links_are_excluded(self):
        state = self.state()
        state["candidates"] += [
            {"title": "Order received", "url": "javascript:alert(1)"},
            {"title": "Order received", "url": "https://user:pass@acme.example/a.pdf"},
            {
                "title": "Order received",
                "url": "https://acme.example/future.pdf",
                "date": "2999-01-01",
            },
        ]
        self.assertEqual(len(events.developments("ACME.NS", state)["items"]), 2)

    def test_follow_up_is_a_lead_not_an_automatically_confirmed_application(self):
        state = {
            "documents": [
                {
                    "id": "a",
                    "title": "Annual report",
                    "url": "https://acme.example/report.pdf",
                    "passages": [
                        {
                            "id": "a:p10",
                            "page": 10,
                            "text": "Our company expects to commission the new plant after obtaining approvals.",
                        }
                    ],
                }
            ]
        }
        result = events.developments("ACME.NS", state)
        self.assertEqual(result["follow_up_leads"][0]["status"], "potential_follow_up")
        self.assertNotIn("stage", result["follow_up_leads"][0])

    def test_additional_reader_checks_identity_and_captures_page_hash(self):
        candidate = {
            "title": "Incorporation of subsidiary",
            "url": "https://acme.example/event.pdf",
            "date": "2025-05-02",
        }
        pdf = make_pdf(
            "Acme Industries Limited. Our company incorporated a subsidiary. It has not started commercial operations."
        )
        with patch.object(
            events, "fetch_public", return_value=(pdf, candidate["url"], "application/pdf")
        ):
            result = events.collect_event_documents(profile(), [candidate], [])
        self.assertEqual(len(result["documents"]), 1)
        document = result["documents"][0]
        self.assertEqual(document["passages"][0]["page"], 1)
        self.assertIn("not started", document["passages"][0]["text"])
        self.assertEqual(len(document["id"]), 20)

    def test_reader_rejects_wrong_issuer_and_bounds_attempts(self):
        candidates = [
            {"title": "Order received", "url": f"https://acme.example/{i}.pdf"} for i in range(8)
        ]
        pdf = make_pdf("Unrelated Widgets Limited received an order.")
        with patch.object(
            events, "fetch_public", return_value=(pdf, candidates[0]["url"], "application/pdf")
        ) as fetch:
            result = events.collect_event_documents(profile(), candidates, [])
        self.assertFalse(result["documents"])
        self.assertEqual(fetch.call_count, events.MAX_EVENT_DOCUMENTS)
        self.assertEqual(len(result["attempts"]), events.MAX_EVENT_DOCUMENTS)

    def test_event_documents_invalidate_ai_snapshot(self):
        state = {"documents": []}
        original = research_workflow.corpus_fingerprint(state)
        state["event_documents"] = [
            {
                "id": "event1",
                "url": "https://acme.example/event.pdf",
                "passages": [{"id": "p1", "text": "New disclosure."}],
            }
        ]
        self.assertNotEqual(original, research_workflow.corpus_fingerprint(state))

    def test_passed_estimate_only_creates_review_flag(self):
        payload = {
            "stage": "bid_submitted",
            "expected_date": "2025-01-01",
            "expected_date_kind": "researcher_estimate",
        }
        result = events._decorate(payload, today=date(2025, 1, 2))
        self.assertTrue(result["review_due"])
        self.assertEqual(result["stage"], "bid_submitted")
        self.assertEqual(result["evidence_status"], "user_research_entry")
        payload["stage"] = "lost"
        self.assertFalse(events._decorate(payload, today=date(2025, 1, 2))["review_due"])

    def test_concurrent_observations_cannot_overwrite_each_other(self):
        initial = {
            "title": "Synthetic concurrency fixture",
            "kind": "tender",
            "stage": "bid_submitted",
            "source_url": "https://example.com/fixture",
            "source_quote": "Synthetic fixture for a project history test.",
            "expected_date": None,
        }
        item = events.create_project("test-owner", "ACME.NS", initial)

        def update(_):
            try:
                events.update_project(
                    "test-owner",
                    "ACME.NS",
                    item["id"],
                    {
                        "stage": "preferred_bidder",
                        "source_url": initial["source_url"],
                        "source_quote": initial["source_quote"],
                        "expected_date": None,
                        "expected_version": 1,
                    },
                )
                return 200
            except HTTPException as error:
                return error.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(update, range(2))), [200, 409])
        current = events.list_projects("test-owner", "ACME.NS")["items"][0]
        self.assertEqual((current["version"], len(current["history"])), (2, 2))


class PendingAPITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.storage = patch.object(local_store, "DATA_DIR", Path(self.directory.name))
        self.storage.start()
        self.env = patch.dict(
            os.environ, {"SESSION_SECRET": "test-project-secret-longer-than-thirty-two-characters"}
        )
        self.env.start()
        self.a, self.b = TestClient(app), TestClient(app)
        self.path = "/api/companies/ACME.NS/pending-items"
        self.payload = {
            "title": "Disclosed infrastructure bid",
            "kind": "tender",
            "stage": "bid_submitted",
            "source_url": "https://acme.example/disclosure.pdf",
            "source_quote": "Our company has submitted its bid; the outcome is not announced.",
            "expected_date": "2025-01-01",
            "expected_date_kind": "researcher_estimate",
        }

    def tearDown(self):
        self.a.close()
        self.b.close()
        self.env.stop()
        self.storage.stop()
        self.directory.cleanup()

    def create(self):
        response = self.a.post(self.path, json=self.payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def observation(self, version=1):
        return {
            "stage": "preferred_bidder",
            "source_url": "https://acme.example/followup.pdf",
            "source_quote": "We are the preferred bidder; the final award remains subject to conditions.",
            "expected_version": version,
        }

    def test_workspace_isolation_no_store_and_unverified_label(self):
        item = self.create()
        self.assertEqual(item["evidence_status"], "user_research_entry")
        response = self.a.get(self.path)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(len(response.json()["items"]), 1)
        self.assertEqual(self.b.get(self.path).json()["items"], [])
        update = f"{self.path}/{item['id']}/observations"
        self.assertEqual(self.b.post(update, json=self.observation()).status_code, 404)
        self.assertEqual(self.b.delete(f"{self.path}/{item['id']}?version=1").status_code, 404)
        self.assertEqual(self.a.get("/api/companies/OTHER.NS/pending-items").json()["items"], [])

    def test_append_only_observations_and_stale_updates(self):
        item = self.create()
        update = f"{self.path}/{item['id']}/observations"
        response = self.a.post(update, json=self.observation())
        self.assertEqual(response.status_code, 200)
        current = response.json()
        self.assertEqual(current["version"], 2)
        self.assertEqual(
            [o["stage"] for o in current["history"]], ["bid_submitted", "preferred_bidder"]
        )
        self.assertIsNone(current["expected_date"])
        self.assertEqual(self.a.post(update, json=self.observation()).status_code, 409)
        self.assertEqual(self.a.delete(f"{self.path}/{item['id']}?version=1").status_code, 409)
        self.assertEqual(self.a.delete(f"{self.path}/{item['id']}?version=2").status_code, 200)
        self.assertFalse(self.a.get(self.path).json()["items"])

    def test_invalid_stage_dates_unsafe_url_and_whitespace_are_rejected(self):
        cases = [
            {"stage": "commercial_operations"},
            {"source_url": "http://acme.example/report.pdf"},
            {"source_url": "https://user:pass@acme.example/report.pdf"},
            {"source_date": "2999-01-01"},
            {"expected_date_kind": None},
            {"source_quote": "             "},
            {"title": "  "},
        ]
        for change in cases:
            with self.subTest(change=change):
                self.assertEqual(
                    self.a.post(self.path, json={**self.payload, **change}).status_code, 422
                )

    def test_update_cannot_change_project_type_or_use_another_lifecycle(self):
        item = self.create()
        path = f"{self.path}/{item['id']}/observations"
        self.assertEqual(
            self.a.post(path, json={**self.observation(), "kind": "expansion"}).status_code, 422
        )
        self.assertEqual(
            self.a.post(
                path, json={**self.observation(), "stage": "commercial_operations"}
            ).status_code,
            422,
        )

    def test_developments_endpoint_does_not_fetch_or_generate(self):
        with (
            patch(
                "routers.developments.cached_research",
                return_value={"documents": [], "candidates": []},
            ),
            patch.object(events, "fetch_public") as fetch,
        ):
            result = self.a.get("/api/companies/ACME.NS/developments")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["items"], [])
        fetch.assert_not_called()
