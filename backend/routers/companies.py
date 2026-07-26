from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from services.data_fetcher import get_company_profile, get_chart_data
from services.indicators import compute_indicators_df
from services.screener_engine import get_peers
from services.snowflake_calculator import generate_pros_and_cons, compute_snowflake_scores
from services.nse_stock_master import search_stock_master

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
            "pe": profile.get("pe", 0.0),
            "pb": profile.get("pb", 0.0),
            "roe": profile.get("roe", 0.0),
            "roce": profile.get("roce", 0.0),
            "debt_equity": profile.get("debt_equity", 0.0),
            "div_yield": profile.get("div_yield", 0.0),
            "revenue_growth_3yr": profile.get("revenue_growth_3yr", 0.0),
            "eps_growth_3yr": profile.get("eps_growth_3yr", 0.0),
            "promoter_holding": profile.get("promoter_holding", 0.0),
            "pledged_shares_pct": profile.get("pledged_shares_pct", 0.0),
            "market_cap": profile.get("market_cap", 0.0),
            "current_price": profile.get("current_price", 0.0),
            "day_change": profile.get("day_change", 0.0),
            "day_change_pct": profile.get("day_change_pct", 0.0),
        }
        
        result = dict(profile)
        result["fundamentals"] = fundamentals
        result["snowflake_scores"] = scores
        result["pros_cons"] = {
            "pros": pros,
            "cons": cons
        }
        result["pros"] = pros
        result["cons"] = cons
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/chart")
def get_company_chart(ticker: str, period: str = Query("1y"), interval: str = Query("1d")):
    try:
        chart_res = get_chart_data(ticker, period=period, interval=interval)
        bars = chart_res.get("bars", [])
        if not bars:
            return {"ticker": ticker, "bars": [], "data_source": chart_res.get("data_source", "unavailable")}

        # Convert to pandas DataFrame for indicator computation
        df = pd.DataFrame(bars)
        df_indicators = compute_indicators_df(df)
        
        # Replace NaN values with None for JSON serialization
        records = df_indicators.where(pd.notnull(df_indicators), None).to_dict(orient="records")

        return {
            "ticker": ticker, 
            "period": period, 
            "interval": interval, 
            "bars": records,
            "data_source": chart_res.get("data_source", "live")
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
        from services.data_fetcher import get_company_financials
        return get_company_financials(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/shareholding")
def get_company_shareholding_endpoint(ticker: str):
    try:
        from services.data_fetcher import get_company_shareholding
        return get_company_shareholding(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

