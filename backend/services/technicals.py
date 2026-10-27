import pandas as pd

from services.data_fetcher import get_chart_data
from services.indicators import compute_indicators


def get_technicals(ticker):
    stock = get_chart_data(ticker, period="2y")
    bars = stock.get("bars", [])
    if not bars:
        return {"as_of": None, "message": "Daily price history is unavailable."}
    df = compute_indicators(pd.DataFrame(bars))
    latest = df.iloc[-1]

    def distance(column):
        value = latest.get(column)
        return (
            round((float(latest["close"]) / float(value) - 1) * 100, 2)
            if pd.notna(value) and value > 0
            else None
        )

    benchmark = get_chart_data("^NSEI", period="2y").get("bars", [])
    returns = {
        "stock_return_pct": None,
        "benchmark_return_pct": None,
        "relative_return_pp": None,
        "comparison_start": None,
    }
    if benchmark:
        aligned = (
            pd.DataFrame(bars)[["time", "close"]]
            .merge(
                pd.DataFrame(benchmark)[["time", "close"]],
                on="time",
                suffixes=("_stock", "_benchmark"),
            )
            .sort_values("time")
        )
        cutoff = (pd.Timestamp(latest["time"]) - pd.Timedelta(days=365)).date().isoformat()
        aligned = aligned[aligned["time"] >= cutoff]
        if len(aligned) > 1:
            first, last = aligned.iloc[0], aligned.iloc[-1]
            # Require the latest stock and benchmark bar to be the same date.
            if last["time"] == latest["time"]:
                sr = (last["close_stock"] / first["close_stock"] - 1) * 100
                br = (last["close_benchmark"] / first["close_benchmark"] - 1) * 100
                returns = {
                    "stock_return_pct": round(sr, 2),
                    "benchmark_return_pct": round(br, 2),
                    "relative_return_pp": round(sr - br, 2),
                    "comparison_start": first["time"],
                }
    return {
        "as_of": latest["time"],
        **returns,
        "sma50_distance_pct": distance("SMA_50"),
        "sma200_distance_pct": distance("SMA_200"),
        "rsi14": round(float(latest["RSI_14"]), 2) if pd.notna(latest["RSI_14"]) else None,
        "methodology": "Yahoo Finance split/dividend-adjusted daily closes. Comparison uses common dates from the last calendar year, or available history for newer listings. Nifty 50 is a price index; stock adjustment includes dividends, so the comparison is not a total-return index comparison. No index or SMA values are fabricated.",
    }
