import math
from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from services.data_fetcher import (
    get_company_profile,
    get_chart_data,
    get_company_financials,
    get_quarterly_results,
    get_historical_ratios,
    get_company_shareholding,
)
from services.indicators import compute_indicators_df
from services.screener_engine import get_peers
from services.snowflake_calculator import generate_pros_and_cons, compute_snowflake_scores
from services.nse_stock_master import search_stock_master

def sanitize_nan_values(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_nan_values(v) for v in obj]
    return obj

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/search")
def search_company_tickers(q: str = Query("", min_length=1)):
    try:
        results = search_stock_master(q)
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}")
def get_company(ticker: str):
    try:
        profile = get_company_profile(ticker)
        scores = compute_snowflake_scores(profile)
        pros, cons = generate_pros_and_cons(profile)

        fundamentals = {
            "pe": profile.get("pe"),
            "pb": profile.get("pb"),
            "eps": profile.get("eps"),
            "book_value": profile.get("book_value"),
            "face_value": profile.get("face_value", 10.0),
            "week_high_52": profile.get("week_high_52"),
            "week_low_52": profile.get("week_low_52"),
            "roe": profile.get("roe"),
            "roce": profile.get("roce"),
            "debt_equity": profile.get("debt_equity"),
            "div_yield": profile.get("div_yield", 0.0),
            "revenue_growth_3yr": profile.get("revenue_growth_3yr"),
            "eps_growth_3yr": profile.get("eps_growth_3yr"),
            "promoter_holding": profile.get("promoter_holding"),
            "pledged_shares_pct": profile.get("pledged_shares_pct", 0.0),
            "market_cap": profile.get("market_cap", 0.0),
            "market_cap_cr": profile.get("market_cap_cr", 0.0),
            "current_price": profile.get("current_price", 0.0),
            "day_change": profile.get("day_change", 0.0),
            "day_change_pct": profile.get("day_change_pct", 0.0),
            "current_ratio": profile.get("current_ratio"),
            "interest_coverage": profile.get("interest_coverage"),
            "payout_ratio": profile.get("payout_ratio"),
        }

        result = dict(profile)
        result["fundamentals"] = fundamentals
        result["snowflake_scores"] = scores
        result["pros_cons"] = {"pros": pros, "cons": cons}
        result["pros"] = pros
        result["cons"] = cons
        return result

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/chart")
def get_company_chart(
    ticker: str,
    period: str = Query("1y"),
    interval: str = Query("1d"),
):
    try:
        # Map frontend period strings to yfinance period strings
        period_map = {
            "1m": "1mo", "6m": "6mo", "1y": "1y",
            "3y": "3y",  "5y": "5y",  "10y": "10y", "max": "max",
            # pass-through if already correct
            "1mo": "1mo", "6mo": "6mo",
        }
        yf_period = period_map.get(period.lower(), period)

        chart_res = get_chart_data(ticker, period=yf_period, interval=interval)
        bars = chart_res.get("bars", [])
        if not bars:
            return {"ticker": ticker, "bars": [], "data_source": chart_res.get("data_source", "unavailable")}

        df = pd.DataFrame(bars)
        df_indicators = compute_indicators_df(df)
        records = df_indicators.to_dict(orient="records")
        clean_records = sanitize_nan_values(records)

        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "bars": clean_records,
            "data_source": chart_res.get("data_source", "live"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/peers")
def get_company_peers(ticker: str):
    try:
        peers_list = get_peers(ticker)
        return {"ticker": ticker, "peers": peers_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/pros-cons")
def get_company_pros_cons(ticker: str):
    try:
        profile = get_company_profile(ticker)
        pros, cons = generate_pros_and_cons(profile)
        return {"ticker": ticker, "pros": pros, "cons": cons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/financials")
def get_company_financials_endpoint(ticker: str):
    try:
        return get_company_financials(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/quarterly-results")
def get_company_quarterly_results(ticker: str):
    """Returns 8-12 quarters of P&L data."""
    try:
        return get_quarterly_results(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/ratios")
def get_company_ratios(ticker: str):
    """Returns 5-10 years of historical key financial ratios."""
    try:
        return get_historical_ratios(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/shareholding")
def get_company_shareholding_endpoint(ticker: str):
    try:
        return get_company_shareholding(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/forensic")
def get_company_forensic(ticker: str):
    """Returns Ind AS Forensic Accounting Metrics (Altman Z'-Score, Beneish M-Score, Cash Conversion Cycle)."""
    try:
        profile = get_company_profile(ticker)
        from services.forensic_engine import compute_forensic_metrics
        return compute_forensic_metrics(profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/valuation-bands")
def get_company_valuation_bands(ticker: str):
    """Returns 5-Year Valuation Bands (PE/PB Median ± 1SD/2SD) and Reverse DCF Market Implied Growth."""
    try:
        profile = get_company_profile(ticker)
        current_price = profile.get("current_price") or 100.0
        pe = profile.get("pe") or 20.0
        pb = profile.get("pb") or 3.0
        from services.valuation_bands import compute_valuation_bands
        return compute_valuation_bands(ticker, current_price, pe, pb)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/supply-chain")
def get_company_supply_chain_endpoint(ticker: str):
    """Returns Bloomberg SPLC-style Supply Chain & Value Chain Graph for Indian Equities."""
    try:
        from services.supply_chain import get_company_supply_chain
        return get_company_supply_chain(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/{ticker}/research-notes")
def get_research_notes(ticker: str):
    """Research digest — rule-based flags + links to official filings."""
    try:
        from services.pseudo_brain import get_company_research_notes
        return get_company_research_notes(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
