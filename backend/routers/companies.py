import math
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Query, Response

from services.data_fetcher import (
    get_chart_data,
    get_company_financials,
    get_company_profile,
    get_company_shareholding,
    get_historical_ratios,
    get_quarterly_results,
)
from services.deep_dive import DeepDiveRequest, generate_company_deep_dive
from services.indicators import compute_indicators
from services.nse_stock_master import search_stock_master
from services.screener_engine import get_peers, snapshot
from services.snowflake_calculator import compute_snowflake_scores, generate_pros_and_cons

router = APIRouter(prefix="/api/companies", tags=["companies"])


def sanitize_nan_values(value):
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: sanitize_nan_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_nan_values(v) for v in value]
    return value


@router.get("/search")
def search_company_tickers(q: str = Query(min_length=1, max_length=60)):
    return {"query": q, "results": search_stock_master(q)}


@router.get("/{ticker}")
def get_company(ticker: str):
    profile = get_company_profile(ticker)
    scores = compute_snowflake_scores(profile)
    pros, cons = generate_pros_and_cons(profile)
    keys = (
        "pe",
        "pb",
        "eps",
        "book_value",
        "face_value",
        "week_high_52",
        "week_low_52",
        "roe",
        "roce",
        "debt_equity",
        "div_yield",
        "revenue_growth_3yr",
        "eps_growth_3yr",
        "promoter_holding",
        "pledged_shares_pct",
        "market_cap",
        "market_cap_cr",
        "current_price",
        "day_change",
        "day_change_pct",
        "current_ratio",
        "interest_coverage",
        "payout_ratio",
        "fcf_per_share",
    )
    return sanitize_nan_values(
        {
            **profile,
            "fundamentals": {key: profile.get(key) for key in keys},
            "snowflake_scores": scores,
            "pros": pros,
            "cons": cons,
            "pros_cons": {"pros": pros, "cons": cons},
        }
    )


@router.get("/{ticker}/chart")
def get_company_chart(
    ticker: str,
    period: Literal["1m", "1mo", "3mo", "6m", "6mo", "1y", "2y", "3y", "5y", "10y", "max"] = "1y",
    interval: Literal["1d", "1wk", "1mo"] = "1d",
):
    chart = get_chart_data(
        ticker, period={"1m": "1mo", "6m": "6mo"}.get(period, period), interval=interval
    )
    if chart.get("bars"):
        chart = {
            **chart,
            "bars": sanitize_nan_values(
                compute_indicators(pd.DataFrame(chart["bars"])).to_dict(orient="records")
            ),
        }
    return chart


@router.get("/{ticker}/peers")
def get_company_peers(ticker: str):
    return {
        "ticker": ticker,
        "peers": get_peers(ticker),
        "coverage": snapshot(refresh=False)[1],
        "basis": "Same industry within the covered research universe.",
    }


@router.get("/{ticker}/pros-cons")
def get_company_pros_cons(ticker: str):
    pros, cons = generate_pros_and_cons(get_company_profile(ticker))
    return {"ticker": ticker, "pros": pros, "cons": cons}


@router.get("/{ticker}/financials")
def get_company_financials_endpoint(ticker: str):
    return get_company_financials(ticker)


@router.get("/{ticker}/quarterly-results")
def get_company_quarterly_results(ticker: str):
    return get_quarterly_results(ticker)


@router.get("/{ticker}/ratios")
def get_company_ratios(ticker: str):
    return get_historical_ratios(ticker)


@router.get("/{ticker}/shareholding")
def get_company_shareholding_endpoint(ticker: str):
    return get_company_shareholding(ticker)


@router.get("/{ticker}/forensic")
def get_company_forensic(ticker: str):
    from services.forensic_engine import compute_forensic_metrics

    return compute_forensic_metrics(get_company_profile(ticker), get_company_financials(ticker))


@router.get("/{ticker}/valuation-bands")
def get_company_valuation_bands(ticker: str):
    from services.valuation_bands import compute_valuation_bands

    profile = get_company_profile(ticker)
    return compute_valuation_bands(
        ticker,
        profile.get("current_price"),
        profile.get("pe"),
        profile.get("pb"),
        financials={} if profile.get("corporate_action_note") else get_company_financials(ticker),
        chart=get_chart_data(ticker, period="5y", auto_adjust=False),
        fcf_per_share=profile.get("fcf_per_share"),
    )


@router.get("/{ticker}/supply-chain")
def get_company_supply_chain_endpoint(ticker: str):
    from services.supply_chain import get_company_supply_chain

    return get_company_supply_chain(ticker)


@router.get("/{ticker}/intelligence")
def get_company_intelligence_endpoint(ticker: str):
    from services.company_intelligence import get_company_intelligence

    return get_company_intelligence(ticker)


@router.get("/{ticker}/research-notes")
def get_research_notes(ticker: str):
    from services.pseudo_brain import get_company_research_notes

    return get_company_research_notes(ticker)


@router.post("/{ticker}/intelligence")
def generate_company_intelligence_endpoint(
    ticker: str, request: DeepDiveRequest, response: Response
):
    response.headers["Cache-Control"] = "no-store"
    return generate_company_deep_dive(ticker, request)


@router.get("/{ticker}/technicals")
def get_company_technicals(ticker: str):
    from services.technicals import get_technicals

    return sanitize_nan_values(get_technicals(ticker))
