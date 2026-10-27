import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from services import data_fetcher as data
from services import screener_engine as screener
from services.cache_manager import LRUCache
from services.forensic_engine import compute_forensic_metrics
from services.snowflake_calculator import compute_snowflake_scores
from services.valuation_bands import compute_valuation_bands, dcf_value, reverse_dcf


class MarketDataTests(unittest.TestCase):
    def test_short_statement_row_returns_missing_value(self):
        fin = {"income_statement": [{"metric": "Diluted EPS", "values": [25]}]}
        self.assertIsNone(data.financial_value(fin, "income_statement", "Diluted EPS", 1))
        self.assertIsNone(data.financial_value(fin, "income_statement", "Diluted EPS", -2))

    def frames(self):
        dates = [pd.Timestamp(f"{year}-03-31") for year in (2026, 2025, 2024, 2023)]
        fin = pd.DataFrame(
            [[1331, 1210, 1100, 1000], [25, 24, 22, 20], [100, 90, 80, 70]],
            index=["Total Revenue", "Diluted EPS", "Net Income"],
            columns=dates,
        )
        bs = pd.DataFrame(
            [[1000, 900, 800], [500, 450, 400], [100, 90, 80]],
            index=["Total Assets", "Stockholders Equity", "Current Liabilities"],
            columns=dates[:-1],
        )
        cf = pd.DataFrame(
            [[100, 90, 80, 70], [-20, -10, -10, -10]],
            index=["Operating Cash Flow", "Capital Expenditure"],
            columns=dates,
        )
        return fin, bs, cf

    def test_statement_units_and_fiscal_alignment(self):
        fin, bs, cf = self.frames()
        fake = SimpleNamespace(financials=fin, balance_sheet=bs, cashflow=cf)
        with (
            patch.object(data.yf, "Ticker", return_value=fake),
            patch.object(data.cache_manager, "get", return_value=None),
            patch.object(data.cache_manager, "set"),
        ):
            result = data.get_company_financials("TEST.NS")
        eps = next(r for r in result["income_statement"] if r["metric"] == "Diluted EPS")
        assets = next(r for r in result["balance_sheet"] if r["metric"] == "Total Assets")
        self.assertEqual(eps["values"], [20, 22, 24, 25])
        self.assertEqual(eps["unit"], "₹ / share")
        self.assertIsNone(assets["values"][0])
        self.assertEqual(
            result["period_dates"],
            ["2023-03-31", "2024-03-31", "2025-03-31", "2026-03-31"],
        )

    def test_cagr_uses_three_elapsed_years(self):
        fin, _, _ = self.frames()
        self.assertEqual(data._cagr(fin, "Total Revenue"), 10.0)
        self.assertIsNone(data._cagr(fin.iloc[:, :3], "Total Revenue"))

    def test_missing_or_nonfinite_is_not_zero(self):
        for value in [None, float("nan"), float("inf"), "bad"]:
            self.assertIsNone(data._safe_float(value))
        self.assertEqual(data._safe_float(0), 0)

    def test_ticker_normalization_and_indexes(self):
        self.assertEqual(data.normalize_ticker(" tcs "), "TCS.NS")
        self.assertEqual(data.normalize_ticker("500325.BO"), "500325.BO")
        self.assertEqual(data.normalize_ticker("^NSEI"), "^NSEI")
        self.assertEqual(data.normalize_ticker("zomato"), "ETERNAL.NS")
        self.assertEqual(data.normalize_ticker("LTIM"), "LTM.NS")
        self.assertEqual(data.normalize_ticker("TATAMOTORS"), "TMPV.NS")
        with self.assertRaises(ValueError):
            data.normalize_ticker("../secrets")

    def test_chart_uses_inclusive_end_and_explicit_adjustment(self):
        frame = pd.DataFrame(
            {
                "Open": [100],
                "High": [110],
                "Low": [90],
                "Close": [105],
                "Volume": [100],
            },
            index=pd.to_datetime(["2024-01-02"]),
        )
        fake = SimpleNamespace(history=lambda **kwargs: frame)
        with (
            patch.object(data.yf, "Ticker", return_value=fake),
            patch.object(data.cache_manager, "get", return_value=None),
            patch.object(data.cache_manager, "set"),
            patch.object(fake, "history", return_value=frame) as history,
        ):
            result = data.get_chart_data("TCS", start_date="2024-01-01", end_date="2024-01-02")
        self.assertEqual(history.call_args.kwargs["end"], "2024-01-03")
        self.assertTrue(history.call_args.kwargs["auto_adjust"])
        self.assertEqual(len(result["bars"]), 1)

    def test_profile_units_missing_ownership_and_payout(self):
        fin, bs, cf = self.frames()
        info = {
            "currentPrice": 100,
            "previousClose": 90,
            "longName": "Example",
            "currency": "INR",
            "returnOnEquity": 1.2,
            "payoutRatio": 1.2,
            "dividendRate": 0.1,
            "sharesOutstanding": 10,
            "debtToEquity": 3,
            "quoteType": "EQUITY",
        }
        fake = SimpleNamespace(info=info, financials=fin, balance_sheet=bs, cashflow=cf)
        with (
            patch.object(data.yf, "Ticker", return_value=fake),
            patch.object(data.cache_manager, "get", return_value=None),
            patch.object(data.cache_manager, "set"),
        ):
            profile = data.get_company_profile("TEST")
        self.assertEqual(profile["roe"], 120)
        self.assertEqual(profile["payout_ratio"], 120)
        self.assertEqual(profile["div_yield"], 0.1)
        self.assertEqual(profile["debt_equity"], 0.03)
        self.assertIsNone(profile["promoter_holding"])
        self.assertIsNone(profile["pledged_shares_pct"])
        self.assertIsNone(profile["face_value"])
        self.assertEqual(profile["fcf_per_share"], 8)

    def test_no_cross_exchange_fallback(self):
        fake = SimpleNamespace(info={})
        with (
            patch.object(data.yf, "Ticker", return_value=fake) as ticker,
            patch.object(data.cache_manager, "get", return_value=None),
        ):
            with self.assertRaises(ValueError):
                data.get_company_profile("TEST")
        ticker.assert_called_once_with("TEST.NS")


class ModelTests(unittest.TestCase):
    def test_missing_forensics_stays_unavailable(self):
        result = compute_forensic_metrics({"ticker": "EMPTY"})
        self.assertIsNone(result["altman_z"]["score"])
        self.assertIsNone(result["beneish_m"]["score"])
        self.assertIsNone(result["cash_conversion_cycle"]["ccc_days"])
        self.assertEqual(result["promoter_pledge"]["status"], "unavailable")

    def financials(self):
        def rows(mapping):
            return [{"metric": k, "values": v, "unit": "₹ Cr"} for k, v in mapping.items()]

        return {
            "period_dates": ["2023-03-31", "2024-03-31"],
            "income_statement": rows(
                {
                    "Total Revenue": [100, 120],
                    "Gross Profit": [40, 48],
                    "Cost Of Revenue": [60, 72],
                    "Operating Income": [10, 12],
                    "SG&A": [10, 12],
                    "Depreciation": [5, 6],
                    "Net Income": [8, 9],
                }
            ),
            "balance_sheet": rows(
                {
                    "Total Assets": [150, 180],
                    "Current Assets": [50, 60],
                    "Current Liabilities": [30, 36],
                    "Retained Earnings": [20, 25],
                    "Total Equity": [70, 84],
                    "Total Liabilities": [80, 96],
                    "Fixed Assets / PPE": [70, 84],
                    "Receivables": [10, 12],
                    "Inventory": [8, 10],
                    "Payables": [6, 8],
                    "Total Debt": [40, 48],
                    "Long Term Debt": [25, 30],
                }
            ),
            "cash_flow": rows({"Operating Cash Flow": [10, 12]}),
        }

    def test_model_known_answer(self):
        result = compute_forensic_metrics(
            {"ticker": "TEST", "sector": "Industrials"}, self.financials()
        )
        expected = 6.56 * (60 - 36) / 180 + 3.26 * 25 / 180 + 6.72 * 12 / 180 + 1.05 * 84 / 96
        self.assertAlmostEqual(result["altman_z"]["score"], round(expected, 3))
        m = -4.84 + 0.920 + 0.528 + 0.404 + 0.892 * 1.2 + 0.115 - 0.172 + 4.679 * (-3 / 180) - 0.327
        self.assertAlmostEqual(result["beneish_m"]["score"], round(m, 3))
        self.assertAlmostEqual(
            result["cash_conversion_cycle"]["ccc_days"],
            round(9 / 72 * 365 + 11 / 120 * 365 - 7 / 72 * 365, 1),
        )

    def test_missing_annual_year_not_treated_as_consecutive(self):
        fin = self.financials()
        fin["period_dates"] = ["2021-03-31", "2024-03-31"]
        result = compute_forensic_metrics({"sector": "Industrials"}, fin)
        self.assertIsNone(result["beneish_m"]["score"])
        self.assertIsNone(result["cash_conversion_cycle"]["ccc_days"])

    def test_financial_institutions_not_scored(self):
        result = compute_forensic_metrics({"sector": "Financial Services"}, self.financials())
        self.assertIsNone(result["altman_z"]["score"])
        self.assertIsNone(result["beneish_m"]["score"])
        self.assertIsNone(result["cash_conversion_cycle"]["ccc_days"])

    def test_reverse_dcf_depends_on_actual_fcf(self):
        self.assertNotEqual(
            reverse_dcf(100, 5)["implied_growth_pct"],
            reverse_dcf(100, 10)["implied_growth_pct"],
        )
        solved = reverse_dcf(100, 5)["implied_growth_pct"]
        self.assertAlmostEqual(dcf_value(5, solved), 100, delta=0.1)
        self.assertIsNone(reverse_dcf(100, None)["implied_growth_pct"])
        self.assertIsNone(reverse_dcf(100, -2)["implied_growth_pct"])

    def test_dcf_rejects_invalid_discount(self):
        with self.assertRaises(ValueError):
            dcf_value(5, 10, 4, 4)

    def test_valuation_never_simulates_missing_history(self):
        result = compute_valuation_bands("TEST", 100, 20, 3)
        self.assertIsNone(result["pe_bands"])
        self.assertEqual(result["observations"], [])
        self.assertIsNone(result["reverse_dcf"]["implied_growth_pct"])

    def test_valuation_observations_use_matching_dates(self):
        fin = {
            "period_dates": ["2022-03-31", "2023-03-31", "2024-03-31"],
            "income_statement": [{"metric": "Diluted EPS", "values": [10, 10, 10]}],
            "balance_sheet": [
                {"metric": "Total Equity", "values": [1, 1, 1]},
                {"metric": "Shares Outstanding", "values": [100000, 100000, 100000]},
            ],
        }
        bars = [
            {"time": "2022-03-31", "close": 100},
            {"time": "2023-03-31", "close": 200},
            {"time": "2024-03-28", "close": 300},
        ]
        result = compute_valuation_bands("TEST", 400, 40, 4, fin, {"bars": bars}, 5)
        self.assertEqual(result["pe_bands"]["mean"], 20)
        self.assertEqual(result["pe_bands"]["sample_count"], 3)
        self.assertEqual(result["pb_bands"]["median"], 2)

    def test_missing_checklist_inputs_do_not_pass(self):
        score = compute_snowflake_scores({})
        self.assertEqual(score["total"], 0)
        self.assertTrue(all(v == "none" for v in score["data_confidence"].values()))

    def test_negative_pe_not_value(self):
        score = compute_snowflake_scores({"pe": -3, "pb": -1})
        self.assertEqual(score["value"], 0)


class InfrastructureTests(unittest.TestCase):
    def test_cache_ttl_lru_and_copy_isolation(self):
        cache = LRUCache(capacity=2)
        cache.set("a", {"x": [1]}, ttl=5)
        value = cache.get("a")
        value["x"].append(2)
        self.assertEqual(cache.get("a"), {"x": [1]})
        cache.set("b", 2)
        cache.get("a")
        cache.set("c", 3)
        self.assertIsNone(cache.get("b"))
        cache.set("now", 4, ttl=0)
        self.assertIsNone(cache.get("now"))

    def test_screener_missing_inputs_never_pass(self):
        stocks = [
            {"ticker": "MISSING", "debt_equity": None, "pledged_shares_pct": None},
            {"ticker": "ZERO", "debt_equity": 0, "pledged_shares_pct": 0},
        ]
        with patch.object(screener, "snapshot", return_value=(stocks, {})):
            self.assertEqual(
                [s["ticker"] for s in screener.filter_stocks({"max_debt_equity": 0})],
                ["ZERO"],
            )
            self.assertEqual(
                [s["ticker"] for s in screener.filter_stocks({"max_pledged": 0})],
                ["ZERO"],
            )

    def test_screener_nulls_sort_last(self):
        stocks = [
            {"ticker": "NONE", "pe": None},
            {"ticker": "A", "pe": 10},
            {"ticker": "B", "pe": 20},
        ]
        with patch.object(screener, "snapshot", return_value=(stocks, {})):
            self.assertEqual(
                [s["ticker"] for s in screener.filter_stocks({"sort_by": "pe", "order": "asc"})],
                ["A", "B", "NONE"],
            )
