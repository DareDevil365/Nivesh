import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pydantic import ValidationError

from schemas import Rule, Strategy
from services import backtest_engine as engine
from services.behavior_engine import analyze_trade_psychology
from services.indicators import compute_custom_indicator
from services.trade_parser import Trade, parse_trade_csv


class StrategyTests(unittest.TestCase):
    def test_indicator_specific_defaults(self):
        macd = Rule(indicator="MACD", condition="crosses_above")
        self.assertEqual((macd.params.fast_period, macd.params.slow_period), (12, 26))
        bollinger = Rule(indicator="BOLLINGER", condition="touches_lower")
        self.assertEqual(bollinger.params.period, 20)
        sma = Rule(indicator="SMA_CROSS", condition="crosses_above")
        self.assertEqual((sma.params.fast_period, sma.params.slow_period), (20, 50))

    def frame(self):
        return pd.DataFrame(
            {
                "time": pd.date_range("2024-01-01", periods=100).strftime("%Y-%m-%d"),
                "close": 100 + np.sin(np.arange(100) / 4) * 20,
                "open": 100,
                "high": 125,
                "low": 75,
                "volume": 1000,
            }
        )

    def test_all_supported_indicators_generate_signals(self):
        df = self.frame()
        for indicator in ("RSI", "SMA_CROSS", "EMA_CROSS", "MACD", "BOLLINGER"):
            with self.subTest(indicator=indicator):
                rule = Rule(
                    indicator=indicator,
                    condition="touches_lower" if indicator == "BOLLINGER" else "crosses_above",
                    value=50,
                    params={
                        "period": 5,
                        "fast_period": 3,
                        "slow_period": 8,
                        "signal_period": 3,
                        "std_dev": 1,
                    },
                )
                self.assertGreater(int(engine.rule_signal(df, rule).sum()), 0)

    def test_cross_is_an_event_not_a_level(self):
        df = self.frame()
        df["close"] = np.arange(100) + 100
        rule = Rule(
            indicator="SMA_CROSS",
            condition="crosses_above",
            params={"fast_period": 2, "slow_period": 3},
        )
        self.assertEqual(engine.rule_signal(df, rule).sum(), 0)

    def test_indicator_periods_change_output(self):
        df = self.frame()
        a = compute_custom_indicator(df, "RSI", {"period": 2})["RSI_2"]
        b = compute_custom_indicator(df, "RSI", {"period": 28})["RSI_28"]
        self.assertFalse(a.equals(b))
        self.assertTrue(b.iloc[:28].isna().all())

    def test_flat_rsi_is_neutral(self):
        df = self.frame()
        df["close"] = 100
        self.assertEqual(compute_custom_indicator(df, "RSI", {"period": 14})["RSI_14"].iloc[-1], 50)

    def run_engine(self, bars=None, capital=1000, **kwargs):
        if bars is None:
            bars = [
                {
                    "time": d.strftime("%Y-%m-%d"),
                    "open": 120,
                    "high": 131,
                    "low": 119,
                    "close": 130,
                    "volume": 1000,
                }
                for d in pd.date_range("2024-01-01", periods=12)
            ]
            bars[0].update(open=100, high=101, low=99, close=100)
        signals = pd.Series([True] + [False] * (len(bars) - 1))
        exits = pd.Series([False] * len(bars))
        with (
            patch.object(engine, "get_chart_data", return_value={"bars": bars}) as fetch,
            patch.object(engine, "rule_signal", side_effect=[signals, exits]),
        ):
            result = engine.run_backtest(
                "TEST",
                {"indicator": "RSI"},
                {"indicator": "RSI", "condition": "crosses_above", "value": 70},
                initial_capital=capital,
                start_date="2024-01-01",
                end_date="2024-01-12",
                stop_loss_pct=kwargs.pop("stop_loss_pct", 0),
                take_profit_pct=kwargs.pop("take_profit_pct", 0),
                cost_bps=kwargs.pop("cost_bps", 0),
                slippage_bps=kwargs.pop("slippage_bps", 0),
                **kwargs,
            )
        return result, fetch

    def test_next_open_and_end_liquidation(self):
        result, fetch = self.run_engine()
        self.assertEqual(result["trade_log"][0]["entry_date"], "2024-01-02")
        self.assertEqual(result["trade_log"][0]["entry_price"], 120)
        self.assertEqual(result["trade_log"][0]["exit_reason"], "end_of_period")
        self.assertEqual(result["final_capital"], 1080)
        self.assertLess(fetch.call_args.kwargs["start_date"], "2024-01-01")

    def test_costs_reduce_capital(self):
        result, _ = self.run_engine(cost_bps=10, slippage_bps=5)
        plain, _ = self.run_engine()
        self.assertLess(result["final_capital"], plain["final_capital"])
        self.assertGreater(result["total_costs"], 0)
        self.assertGreater(result["trade_log"][0]["costs"], 0)

    def test_cannot_afford_unit_does_not_create_trade(self):
        result, _ = self.run_engine(capital=50)
        self.assertEqual(result["total_trades"], 0)
        self.assertEqual(result["final_capital"], 50)

    def test_stop_handles_gap_and_ambiguous_bar(self):
        bars = [
            {
                "time": d.strftime("%Y-%m-%d"),
                "open": 120,
                "high": 121,
                "low": 119,
                "close": 120,
                "volume": 1000,
            }
            for d in pd.date_range("2024-01-01", periods=12)
        ]
        bars[2].update(open=80, high=90, low=70, close=85)
        result, _ = self.run_engine(bars=bars, stop_loss_pct=10, take_profit_pct=10)
        self.assertEqual(result["trade_log"][0]["exit_price"], 80)
        bars[2].update(open=120, high=150, low=90, close=120)
        result, _ = self.run_engine(bars=bars, stop_loss_pct=10, take_profit_pct=10)
        self.assertEqual(result["trade_log"][0]["exit_price"], 108)

    def test_strategy_validation(self):
        invalid = [
            {"position_sizing": {"amount": 0}},
            {"cost_bps": float("nan")},
            {"entry_rule": {"indicator": "FAKE"}},
            {"date_range": {"start": "1992-01-01", "end": "1992-12-01"}},
            {"date_range": {"start": "2024-12-01", "end": "2024-01-01"}},
            {
                "entry_rule": {
                    "indicator": "MACD",
                    "params": {"fast_period": 30, "slow_period": 20},
                }
            },
            {"entry_rule": {"indicator": "BOLLINGER", "condition": "crosses_above"}},
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                Strategy.model_validate(payload)

    def test_demerger_crossing_range_rejected(self):
        with self.assertRaisesRegex(ValueError, "demerger"):
            engine.run_backtest(
                "TATAMOTORS",
                {"indicator": "RSI"},
                {"indicator": "RSI", "condition": "crosses_above"},
                start_date="2024-01-01",
                end_date="2026-01-01",
            )


class TradeTests(unittest.TestCase):
    def test_fifo_partial_fills_no_invented_profit(self):
        text = "symbol,trade_date,trade_type,quantity,price\nTCS,2024-01-01,buy,10,100\nTCS,2024-01-02,buy,5,120\nTCS,2024-01-03,sell,12,90\n"
        result = parse_trade_csv(text, "zerodha")
        self.assertEqual(result["trade_count"], 2)
        self.assertEqual([t["qty"] for t in result["trades"]], [10, 2])
        self.assertEqual([t["sell_price"] for t in result["trades"]], [90, 90])
        self.assertTrue(any("remain open" in w for w in result["warnings"]))

    def test_csv_quotes_and_bom(self):
        text = '\ufeffticker,buy_date,buy_price,sell_date,sell_price,qty,costs\nTCS,01/01/2024,"1,000",02/01/2024,"1,100",2,10\n'
        result = parse_trade_csv(text)
        self.assertEqual(result["trades"][0]["buy_price"], 1000)
        self.assertEqual(result["trades"][0]["costs"], 10)

    def test_invalid_rows_reported_not_defaulted(self):
        text = "ticker,buy_date,buy_price,sell_date,sell_price,qty\nTCS,2024-01-01,0,2024-02-01,120,10\nTCS,2024-01-01,100,2024-02-01,90,10\n"
        result = parse_trade_csv(text)
        self.assertEqual(result["trade_count"], 1)
        self.assertEqual(result["errors"][0]["line"], 2)

    def test_no_closed_history_rejected(self):
        with self.assertRaises(ValueError):
            parse_trade_csv(
                "symbol,trade_date,trade_type,quantity,price\nTCS,2024-01-01,buy,10,100\n"
            )

    def test_reversed_dates_rejected(self):
        with self.assertRaises(ValidationError):
            Trade(
                ticker="TCS",
                buy_date="2024-02-01",
                sell_date="2024-01-01",
                buy_price=100,
                sell_price=110,
                qty=1,
            )

    def trades(self):
        return [
            {
                "ticker": "TCS",
                "buy_date": "2020-01-01",
                "sell_date": "2020-01-02",
                "buy_price": 100,
                "sell_price": 90,
                "qty": 10,
            },
            {
                "ticker": "TCS",
                "buy_date": "2024-01-01",
                "sell_date": "2024-01-02",
                "buy_price": 100,
                "sell_price": 110,
                "qty": 20,
            },
        ]

    def test_years_apart_not_revenge_pattern(self):
        metrics = analyze_trade_psychology(self.trades())
        self.assertEqual(metrics["revenge_score"], 0)
        self.assertIsNone(metrics["overtrading_score"])

    def test_behavior_chronological_and_costs(self):
        trades = self.trades()
        trades[1]["buy_date"] = "2020-01-03"
        trades[1]["sell_date"] = "2020-01-04"
        trades[1]["costs"] = 20
        a = analyze_trade_psychology(trades)
        b = analyze_trade_psychology(list(reversed(trades)))
        self.assertEqual(a, b)
        self.assertEqual(a["revenge_score"], 50)
        self.assertEqual(a["total_pnl"], 80)

    def test_insufficient_data_not_fabricated(self):
        metrics = analyze_trade_psychology(self.trades()[:1])
        self.assertTrue(metrics["insufficient_data"])
        self.assertIsNone(metrics["win_rate_pct"])
