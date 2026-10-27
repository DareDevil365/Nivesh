import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from routers import watchlist
from services import local_store


class WorkspaceAPITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.storage = patch.object(local_store, "DATA_DIR", Path(self.directory.name))
        self.storage.start()
        self.env = patch.dict(
            os.environ,
            {
                "SESSION_SECRET": "test-secret-with-at-least-thirty-two-characters",
                "COOKIE_SECURE": "false",
            },
        )
        self.env.start()
        self.profile = patch.object(
            watchlist,
            "get_company_profile",
            return_value={
                "name": "Example",
                "sector": "Technology",
                "current_price": 100,
                "day_change": 1,
                "day_change_pct": 1,
                "pe": 20,
                "roe": 15,
                "quote_as_of": "2024-01-01T10:00:00Z",
            },
        )
        self.profile.start()
        self.a = TestClient(app)
        self.b = TestClient(app)

    def tearDown(self):
        self.a.close()
        self.b.close()
        self.profile.stop()
        self.env.stop()
        self.storage.stop()
        self.directory.cleanup()

    def test_signed_http_only_workspace_cookie(self):
        result = self.a.get("/api/workspace")
        self.assertEqual(result.status_code, 200)
        self.assertIn("HttpOnly", result.headers["set-cookie"])
        self.assertIn("SameSite=lax", result.headers["set-cookie"])
        self.assertEqual(result.headers["cache-control"], "no-store")

    def test_watchlists_isolated_and_persistent_across_clients(self):
        result = self.a.post("/api/watchlist/item", json={"ticker": "TCS"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.a.get("/api/watchlist").json()["count"], 1)
        self.assertEqual(self.b.get("/api/watchlist").json()["count"], 0)
        reopened = TestClient(app)
        reopened.cookies.update(self.a.cookies)
        try:
            self.assertEqual(reopened.get("/api/watchlist").json()["count"], 1)
        finally:
            reopened.close()

    def test_forged_cookie_gets_new_workspace(self):
        self.a.post("/api/watchlist/item", json={"ticker": "TCS"})
        self.b.cookies.set(local_store.COOKIE, "a" * 64 + ".invalid")
        self.assertEqual(self.b.get("/api/watchlist").json()["count"], 0)

    def test_symbol_alias_dedup_and_normalized_delete(self):
        self.a.post("/api/watchlist/item", json={"ticker": "TCS"})
        result = self.a.post("/api/watchlist/item", json={"ticker": "tcs.ns"})
        self.assertEqual(result.json()["status"], "exists")
        self.a.delete("/api/watchlist/item?ticker=tcs")
        self.assertEqual(self.a.get("/api/watchlist").json()["count"], 0)

    def test_missing_quote_does_not_remove_saved_stock(self):
        self.a.post("/api/watchlist/item", json={"ticker": "TCS"})
        with patch.object(watchlist, "get_company_profile", side_effect=ValueError("Unavailable")):
            result = self.a.get("/api/watchlist").json()
        self.assertEqual(result["count"], 1)
        self.assertFalse(result["items"][0]["available"])
        self.assertIsNone(result["items"][0]["current_price"])

    def test_alert_evaluation_and_owner_protected_delete(self):
        response = self.a.post(
            "/api/watchlist/alerts",
            json={"ticker": "TCS", "condition": "PRICE_ABOVE", "threshold": 90},
        )
        self.assertEqual(response.status_code, 200)
        identifier = response.json()["alert"]["id"]
        result = self.a.get("/api/watchlist/alerts").json()["alerts"]
        self.assertTrue(result[0]["triggered"])
        self.b.delete(f"/api/watchlist/alerts/{identifier}")
        self.assertEqual(len(self.a.get("/api/watchlist/alerts").json()["alerts"]), 1)
        self.a.delete(f"/api/watchlist/alerts/{identifier}")
        self.assertEqual(len(self.a.get("/api/watchlist/alerts").json()["alerts"]), 0)

    def test_invalid_alert_rejected(self):
        for condition, threshold in [
            ("WRONG", 20),
            ("RSI_ABOVE", 101),
            ("PRICE_ABOVE", 0),
        ]:
            self.assertEqual(
                self.a.post(
                    "/api/watchlist/alerts",
                    json={
                        "ticker": "TCS",
                        "condition": condition,
                        "threshold": threshold,
                    },
                ).status_code,
                422,
            )

    def test_reports_are_private(self):
        self.assertEqual(
            self.a.post("/api/reports", json={"description": "Example test feedback"}).status_code,
            200,
        )
        self.assertEqual(len(self.a.get("/api/reports").json()["reports"]), 1)
        self.assertEqual(self.b.get("/api/reports").json()["reports"], [])
        self.assertEqual(self.a.get("/api/reports?limit=-1").status_code, 422)
        self.assertEqual(self.a.post("/api/reports", json={"description": "   "}).status_code, 422)

    def test_backtest_errors_are_validation_responses(self):
        for payload in [
            {"position_sizing": {"amount": 0}},
            {"entry_rule": {"indicator": "UNKNOWN"}},
            {"date_range": {"start": "1992-01-01", "end": "1992-12-31"}},
        ]:
            self.assertEqual(self.a.post("/api/backtest", json=payload).status_code, 422)

    def test_parser_preserves_thresholds_without_sl_contamination(self):
        response = self.a.post(
            "/api/backtest/parse",
            json={
                "text": "RELIANCE.NS buy RSI 14 below 30, sell above 70, stop loss 5% from 2024-01-01 to 2024-12-31"
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        strategy = response.json()["strategy_json"]
        self.assertEqual(strategy["entry_rule"]["value"], 30)
        self.assertEqual(strategy["exit_rule"]["value"], 70)
        self.assertEqual(strategy["entry_rule"]["params"]["period"], 14)
        self.assertEqual(strategy["stop_loss_pct"], 5)

    def test_parser_preserves_inverted_rsi_rules(self):
        result = self.a.post(
            "/api/backtest/parse",
            json={
                "text": "TCS.NS buy RSI above 70 and sell RSI below 30 from 2024-01-01 to 2024-12-31"
            },
        )
        self.assertEqual(result.status_code, 200, result.text)
        rules = result.json()["strategy_json"]
        self.assertEqual(rules["entry_rule"]["condition"], "crosses_above")
        self.assertEqual(rules["entry_rule"]["value"], 70)
        self.assertEqual(rules["exit_rule"]["condition"], "crosses_below")
        self.assertEqual(rules["exit_rule"]["value"], 30)

    def test_provider_outage_is_503(self):
        from services.data_fetcher import MarketDataUnavailable

        with patch(
            "routers.companies.get_company_profile",
            side_effect=MarketDataUnavailable("Provider unavailable"),
        ):
            result = self.a.get("/api/companies/TCS.NS")
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json()["detail"], "Provider unavailable")

    def test_parser_rejects_unsupported_instead_of_guessing(self):
        for text in [
            "Buy stocks whenever they seem cheap",
            "RELIANCE.NS buy intraday RSI below 30 and sell above 70",
        ]:
            self.assertEqual(
                self.a.post("/api/backtest/parse", json={"text": text}).status_code, 422
            )

    def test_empty_behavior_returns_unavailable_metrics(self):
        response = self.a.post("/api/behavior/analyze", json={"trades": []})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["metrics"]["win_rate_pct"])

    def test_upload_rejects_broken_schema(self):
        response = self.a.post("/api/behavior/upload", json={"csv_text": "symbol,price\nTCS,100\n"})
        self.assertEqual(response.status_code, 422)

    def test_body_size_header_limit(self):
        result = self.a.post(
            "/api/behavior/upload",
            content="{}",
            headers={"content-length": "4000000", "content-type": "application/json"},
        )
        self.assertEqual(result.status_code, 413)

    def test_health_timestamp(self):
        result = self.a.get("/health")
        self.assertEqual(result.status_code, 200)
        self.assertNotEqual(result.json()["timestamp"], "live")
