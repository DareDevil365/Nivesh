"""Long-only, all-in, daily-bar research backtester with explicit execution assumptions."""

import math
from datetime import date as calendar_date
from datetime import timedelta

import pandas as pd

from schemas import Rule, Strategy
from services.data_fetcher import get_chart_data, normalize_ticker
from services.indicators import compute_custom_indicator


def rule_signal(frame, rule):
    rule = rule if isinstance(rule, Rule) else Rule.model_validate(rule)
    p = rule.params.model_dump()
    df = compute_custom_indicator(frame, rule.indicator, p)
    if rule.indicator == "RSI":
        difference = df[f"RSI_{p['period']}"] - rule.value
    elif rule.indicator in {"SMA_CROSS", "EMA_CROSS"}:
        name = rule.indicator.split("_")[0]
        difference = df[f"{name}_{p['fast_period']}"] - df[f"{name}_{p['slow_period']}"]
    elif rule.indicator == "MACD":
        difference = df["MACD"] - df["MACD_signal"]
    elif rule.indicator == "BOLLINGER":
        col = (
            f"BBL_{p['period']}_{float(p['std_dev'])}"
            if rule.condition == "touches_lower"
            else f"BBU_{p['period']}_{float(p['std_dev'])}"
        )
        return (
            df["close"] <= df[col] if rule.condition == "touches_lower" else df["close"] >= df[col]
        ).fillna(False)
    previous = difference.shift(1)
    return (
        (difference > 0) & (previous <= 0)
        if rule.condition == "crosses_above"
        else (difference < 0) & (previous >= 0)
    ).fillna(False)


def run_indicator_backtest(
    ticker,
    entry_rule,
    exit_rule,
    initial_capital=100000,
    stop_loss_pct=5,
    take_profit_pct=15,
    start_date=None,
    end_date=None,
    period="5y",
    cost_bps=10,
    slippage_bps=5,
):
    payload = {
        "ticker": ticker,
        "entry_rule": entry_rule,
        "exit_rule": exit_rule,
        "position_sizing": {"amount": initial_capital},
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct,
        "cost_bps": cost_bps,
        "slippage_bps": slippage_bps,
    }
    if start_date or end_date:
        payload["date_range"] = {
            k: v for k, v in {"start": start_date, "end": end_date}.items() if v
        }
    strategy = Strategy.model_validate(payload)
    ticker = normalize_ticker(strategy.ticker)
    start, end = strategy.date_range.start, strategy.date_range.end
    if (
        ticker == "TMPV.NS"
        and start < calendar_date(2025, 10, 24)
        and end >= calendar_date(2025, 10, 1)
    ):
        raise ValueError(
            "This range crosses the Tata Motors 2025 demerger. The engine does not model distributed commercial-vehicle shares. Use a range ending before October 2025 or starting on/after 24 October 2025, and verify corporate-action adjustments."
        )
    warmup = (
        max(
            strategy.entry_rule.params.slow_period,
            strategy.exit_rule.params.slow_period,
            strategy.entry_rule.params.period,
            strategy.exit_rule.params.period,
        )
        * 3
        + 60
    )
    history = get_chart_data(
        ticker,
        period=period,
        interval="1d",
        start_date=(start - timedelta(days=warmup)).isoformat(),
        end_date=end.isoformat(),
        auto_adjust=True,
    )
    if not history.get("bars"):
        raise ValueError(
            history.get("message") or "No price history is available for the requested dates."
        )
    df = (
        pd.DataFrame(history["bars"])
        .drop_duplicates("time")
        .sort_values("time")
        .reset_index(drop=True)
    )
    df["time"] = pd.to_datetime(df["time"])
    df["entry"] = rule_signal(df, strategy.entry_rule).shift(1, fill_value=False)
    df["exit"] = rule_signal(df, strategy.exit_rule).shift(1, fill_value=False)
    available = df[(df["time"] >= pd.Timestamp(start)) & (df["time"] <= pd.Timestamp(end))]
    if len(available) < 10:
        raise ValueError(
            "Fewer than 10 trading bars are available in this date range. Select a longer period supported by the provider."
        )
    cash, shares = float(initial_capital), 0
    entry_price, entry_cost, entry_date = 0.0, 0.0, ""
    fee, slip = cost_bps / 10000, slippage_bps / 10000
    trades, curve = [], []
    total_costs = 0.0
    first_close = float(available.iloc[0]["close"])

    def sell(raw_price, date, reason):
        nonlocal cash, shares, total_costs
        price = raw_price * (1 - slip)
        commission = shares * price * fee
        proceeds = shares * price - commission
        pnl = proceeds - entry_cost
        total_costs += commission + shares * raw_price * slip
        trades.append(
            {
                "entry_date": entry_date,
                "exit_date": date,
                "entry_price": round(entry_price, 4),
                "exit_price": round(price, 4),
                "costs": round(entry_cost - shares * entry_price + commission, 4),
                "shares": shares,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl / entry_cost * 100, 2),
                "win": pnl > 0,
                "exit_reason": reason,
            }
        )
        cash += proceeds
        shares = 0

    for index, row in available.iterrows():
        date = row["time"].date().isoformat()
        if shares and row["exit"]:
            sell(float(row["open"]), date, "signal_next_open")
        elif not shares and row["entry"]:
            raw = float(row["open"])
            entry_price = raw * (1 + slip)
            shares = int(cash // (entry_price * (1 + fee)))
            if shares > 0:
                entry_cost = shares * entry_price * (1 + fee)
                cash -= entry_cost
                total_costs += shares * entry_price * fee + shares * raw * slip
                entry_date = date
        if shares:
            stop = entry_price * (1 - stop_loss_pct / 100) if stop_loss_pct else None
            target = entry_price * (1 + take_profit_pct / 100) if take_profit_pct else None
            # Gaps fill at open; if both barriers are touched, assume the stop occurs first.
            if stop is not None and row["low"] <= stop:
                sell(min(float(row["open"]), stop), date, "stop_loss")
            elif target is not None and row["high"] >= target:
                sell(max(float(row["open"]), target), date, "take_profit")
        if index == available.index[-1] and shares:
            sell(float(row["close"]), date, "end_of_period")
        curve.append(
            {
                "time": date,
                "portfolio_value": round(cash + shares * float(row["close"]), 2),
                "benchmark_value": round(initial_capital * float(row["close"]) / first_close, 2),
            }
        )
    equity = pd.Series([initial_capital] + [p["portfolio_value"] for p in curve], dtype=float)
    daily = equity.pct_change().dropna()
    std = daily.std(ddof=1)
    days = max(1, (available.iloc[-1]["time"] - available.iloc[0]["time"]).days)
    warnings = []
    if (available.iloc[0]["time"].date() - start).days > 7:
        warnings.append(
            "Price history starts after your requested start date. Results use only the available range."
        )
    if len(df[df["time"] < pd.Timestamp(start)]) < warmup / 3 - 20:
        warnings.append(
            "Limited pre-period history; indicators remain inactive until their warm-up is complete."
        )
    return {
        "ticker": ticker,
        "initial_capital": initial_capital,
        "final_capital": round(cash, 2),
        "total_return_pct": round((cash / initial_capital - 1) * 100, 2),
        "cagr": round(((cash / initial_capital) ** (365.25 / days) - 1) * 100, 2)
        if cash > 0
        else -100,
        "max_drawdown_pct": round(float((1 - equity / equity.cummax()).max() * 100), 2),
        "sharpe_ratio": round(float(daily.mean() / std * math.sqrt(252)), 2)
        if pd.notna(std) and std > 0
        else 0,
        "total_trades": len(trades),
        "win_rate_pct": round(sum(t["win"] for t in trades) / len(trades) * 100, 2)
        if trades
        else 0,
        "trade_log": trades,
        "equity_curve": curve,
        "total_costs": round(total_costs, 2),
        "actual_start": curve[0]["time"],
        "actual_end": curve[-1]["time"],
        "warnings": warnings,
        "assumptions": {
            "execution": "Signals at close execute at the next open. End positions are liquidated at final close.",
            "risk": "Daily high/low barriers; stop assumed first when both are touched. Gaps fill at open.",
            "cost_bps_per_side": cost_bps,
            "slippage_bps_per_side": slippage_bps,
            "price_adjustment": "Split and dividend adjusted OHLC; benchmark is the same stock, frictionless buy-and-hold.",
            "limitations": "Long only, one position, whole units, reinvested capital. No taxes, liquidity limits or market impact. Sharpe uses zero risk-free rate. Current symbols introduce survivorship bias.",
        },
    }


run_backtest = run_indicator_backtest
