import math
from statistics import mean, median, pstdev

from services.data_fetcher import financial_value


def dcf_value(fcf_per_share, growth_pct, discount_pct=11, terminal_pct=4, years=5):
    if (
        not all(math.isfinite(v) for v in (fcf_per_share, growth_pct, discount_pct, terminal_pct))
        or fcf_per_share <= 0
        or growth_pct <= -100
        or discount_pct <= terminal_pct
    ):
        raise ValueError(
            "DCF needs positive FCF per share, growth above -100%, and discount rate above terminal growth."
        )
    growth, discount, terminal = (
        growth_pct / 100,
        discount_pct / 100,
        terminal_pct / 100,
    )
    flows = sum(
        fcf_per_share * (1 + growth) ** year / (1 + discount) ** year
        for year in range(1, years + 1)
    )
    terminal_value = (
        fcf_per_share
        * (1 + growth) ** years
        * (1 + terminal)
        / (discount - terminal)
        / (1 + discount) ** years
    )
    return flows + terminal_value


def reverse_dcf(price, fcf):
    empty = {
        "implied_growth_pct": None,
        "discount_rate_wacc_pct": 11,
        "terminal_growth_pct": 4,
        "matrix": None,
        "fcf_per_share": fcf,
        "explanation": "Positive annual free cash flow per share is required. No price-derived cash flow is substituted.",
    }
    if fcf is None or fcf <= 0 or price is None or price <= 0:
        return empty
    lower, upper = -90.0, 100.0
    if not dcf_value(fcf, lower) <= price <= dcf_value(fcf, upper):
        return {
            **empty,
            "explanation": "No solution within -90% to 100% annual growth under these assumptions.",
        }
    for _ in range(80):
        middle = (lower + upper) / 2
        if dcf_value(fcf, middle) < price:
            lower = middle
        else:
            upper = middle
    scenarios = [
        {
            "label": label,
            "growth_pct": growth,
            "discount_pct": 11,
            "value": round(dcf_value(fcf, growth), 2),
        }
        for label, growth in (
            ("Lower growth", 5),
            ("Middle growth", 10),
            ("Higher growth", 15),
        )
    ]
    return {
        **empty,
        "implied_growth_pct": round((lower + upper) / 2, 2),
        "scenarios": scenarios,
        "explanation": "Five-year growth solving a simplified cash-flow-per-share model. Uses reported annual CFO less capex divided by current shares. Fixed 11% discount, 4% terminal growth; no dilution or capital structure forecast.",
    }


def compute_valuation_bands(
    ticker,
    current_price,
    pe=None,
    pb=None,
    financials=None,
    chart=None,
    fcf_per_share=None,
):
    fin, bars = financials or {}, (chart or {}).get("bars", [])
    observations = []
    for i, date in enumerate(fin.get("period_dates", [])):
        eligible = [b for b in bars if b["time"] <= date]
        if not eligible:
            continue
        bar = eligible[-1]
        from datetime import date as dt

        if (dt.fromisoformat(date) - dt.fromisoformat(bar["time"])).days > 7:
            continue
        eps = financial_value(fin, "income_statement", "Diluted EPS", i)
        equity = financial_value(fin, "balance_sheet", "Total Equity", i)
        shares = financial_value(fin, "balance_sheet", "Shares Outstanding", i)
        book = equity * 1e7 / shares if equity is not None and shares and shares > 0 else None
        observations.append(
            {
                "date": date,
                "price_date": bar["time"],
                "pe": round(bar["close"] / eps, 3) if eps and eps > 0 else None,
                "pb": round(bar["close"] / book, 3) if book and book > 0 else None,
            }
        )

    def bands(metric, current):
        vals = [o[metric] for o in observations if o[metric] is not None]
        if len(vals) < 3:
            return None
        center, sd = mean(vals), pstdev(vals)
        return {
            "mean": round(center, 2),
            "median": round(median(vals), 2),
            "plus_1sd": round(center + sd, 2),
            "minus_1sd": round(center - sd, 2),
            "plus_2sd": round(center + 2 * sd, 2),
            "minus_2sd": round(center - 2 * sd, 2),
            "current": current,
            "sample_count": len(vals),
        }

    pe_bands, pb_bands = bands("pe", pe), bands("pb", pb)
    return {
        "ticker": ticker,
        "current_price": current_price,
        "pe_bands": pe_bands,
        "pb_bands": pb_bands,
        "observations": observations,
        "valuation_zone": "Retrospective annual comparison"
        if pe_bands or pb_bands
        else "Insufficient observations",
        "valuation_status": "neutral",
        "valuation_comment": "Annual fiscal-end observations, not a daily five-year valuation history.",
        "methodology": "Annual EPS and year-end book equity/share counts paired with provider fiscal-end closing prices. Statements can be restated and per-share figures can have different split conventions. These retrospective comparisons are not point-in-time data and must not be used as backtest signals. Bands use the mean ± population standard deviation; at least three observations required.",
        "reverse_dcf": reverse_dcf(current_price, fcf_per_share),
    }
