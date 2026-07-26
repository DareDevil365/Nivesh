import math
import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from services.data_fetcher import get_chart_data
from services.indicators import compute_indicators_df

logger = logging.getLogger(__name__)

def run_indicator_backtest(
    ticker: str,
    entry_rule: Dict[str, Any],
    exit_rule: Dict[str, Any],
    initial_capital: float = 100000.0,
    stop_loss_pct: float = 5.0,
    take_profit_pct: Optional[float] = None,
    start_date: Optional[str] = None,
    period: str = "5y"
) -> Dict[str, Any]:
    """
    Deterministic vectorized strategy simulation engine with compounding portfolio math,
    correct CAGR, Sharpe ratio, and Max Drawdown calculations.
    """
    chart_res = get_chart_data(ticker, period=period, interval="1d")
    bars = chart_res.get("bars", [])
    
    if not bars or len(bars) < 10:
        return {"error": f"Insufficient price data available to backtest {ticker}."}

    df = pd.DataFrame(bars)
    df["time"] = pd.to_datetime(df["time"])
    df.sort_values("time", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Filter date range if specified
    if start_date:
        df = df[df["time"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["time"] <= pd.to_datetime(end_date)]
        
    df.reset_index(drop=True, inplace=True)
    if len(df) < 10:
        return {"error": "Date range contains insufficient trading bars for backtest."}

    # Compute technical indicators
    df = compute_indicators_df(df)

    # Parse indicators
    entry_ind = entry_rule.get("indicator", "RSI").upper()
    entry_cond = entry_rule.get("condition", "crosses_below")
    entry_val = float(entry_rule.get("value", 30))

    exit_ind = exit_rule.get("indicator", "RSI").upper()
    exit_cond = exit_rule.get("condition", "crosses_above")
    exit_val = float(exit_rule.get("value", 70))

    cash = initial_capital
    shares = 0
    in_position = False
    entry_price = 0.0
    entry_date = ""

    trade_log = []
    equity_curve = []
    peak_portfolio_val = initial_capital
    max_drawdown_pct = 0.0

    for i in range(len(df)):
        row = df.iloc[i]
        curr_price = float(row["close"])
        curr_date = row["time"].strftime("%Y-%m-%d")

        # Evaluate Signals
        entry_signal = False
        exit_signal = False

        # Entry logic
        if not in_position:
            if entry_ind == "RSI" and "RSI_14" in row:
                rsi_val = row["RSI_14"]
                if not pd.isna(rsi_val):
                    if entry_cond == "crosses_below" and rsi_val < entry_val:
                        entry_signal = True
                    elif entry_cond == "crosses_above" and rsi_val > entry_val:
                        entry_signal = True
            elif entry_ind == "SMA_CROSS" and "SMA_20" in row and "SMA_50" in row:
                if row["SMA_20"] > row["SMA_50"]:
                    entry_signal = True

        # Exit logic
        else:
            if exit_ind == "RSI" and "RSI_14" in row:
                rsi_val = row["RSI_14"]
                if not pd.isna(rsi_val):
                    if exit_cond == "crosses_above" and rsi_val > exit_val:
                        exit_signal = True
                    elif exit_cond == "crosses_below" and rsi_val < exit_val:
                        exit_signal = True
            
            # Risk exits: Stop loss & Take profit
            pnl_pct = ((curr_price - entry_price) / entry_price) * 100
            if stop_loss_pct and pnl_pct <= -abs(stop_loss_pct):
                exit_signal = True
            if take_profit_pct and pnl_pct >= abs(take_profit_pct):
                exit_signal = True

        # Execute Entry
        if entry_signal and not in_position:
            in_position = True
            entry_price = curr_price
            entry_date = curr_date
            shares = int(cash // curr_price)
            cash -= shares * curr_price

        # Execute Exit
        elif exit_signal and in_position:
            in_position = False
            exit_price = curr_price
            proceeds = shares * exit_price
            cash += proceeds
            pnl = proceeds - (shares * entry_price)
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            
            trade_log.append({
                "entry_date": entry_date,
                "exit_date": curr_date,
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "shares": shares,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "win": pnl > 0
            })
            shares = 0

        # Portfolio Tracking
        current_portfolio_val = cash + (shares * curr_price)
        equity_curve.append({
            "time": curr_date,
            "portfolio_value": round(current_portfolio_val, 2),
            "benchmark_value": round(initial_capital * (curr_price / float(df.iloc[0]["close"])), 2)
        })

        if current_portfolio_val > peak_portfolio_val:
            peak_portfolio_val = current_portfolio_val
        dd = (peak_portfolio_val - current_portfolio_val) / peak_portfolio_val * 100.0
        if dd > max_drawdown_pct:
            max_drawdown_pct = dd

    # Final stats computation
    final_val = current_portfolio_val
    total_return_pct = round(((final_val - initial_capital) / initial_capital) * 100.0, 2)
    
    trading_days = max(1, len(df))
    cagr = round((((final_val / initial_capital) ** (252.0 / trading_days)) - 1.0) * 100.0, 2) if final_val > 0 else 0.0

    # Daily returns & Sharpe Ratio
    eq_series = pd.Series([e["portfolio_value"] for e in equity_curve])
    daily_returns = eq_series.pct_change().dropna()
    
    mean_ret = daily_returns.mean()
    std_ret = daily_returns.std()
    sharpe_ratio = round(float((mean_ret / std_ret) * math.sqrt(252)), 2) if std_ret > 0 else 0.0

    wins = [t for t in trade_log if t["win"]]
    win_rate = round((len(wins) / len(trade_log)) * 100.0, 2) if trade_log else 0.0

    return {
        "ticker": ticker,
        "initial_capital": initial_capital,
        "final_capital": round(final_val, 2),
        "total_return_pct": total_return_pct,
        "cagr": cagr,
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": sharpe_ratio,
        "total_trades": len(trade_log),
        "win_rate_pct": win_rate,
        "trade_log": trade_log,
        "equity_curve": equity_curve
    }

# Alias for backward compatibility
run_backtest = run_indicator_backtest

