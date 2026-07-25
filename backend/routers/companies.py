from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from services.data_fetcher import get_company_profile, get_chart_data
from services.indicators import compute_indicators
from services.screener_engine import get_peers

router = APIRouter(prefix="/api/companies", tags=["companies"])

@router.get("/{ticker}")
def get_company(ticker: str):
    try:
        profile = get_company_profile(ticker)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/chart")
def get_company_chart(ticker: str, period: str = Query("1y"), interval: str = Query("1d")):
    try:
        chart_bars = get_chart_data(ticker, period=period, interval=interval)
        if not chart_bars:
            return {"ticker": ticker, "bars": []}

        # Convert to pandas DataFrame for indicator computation
        df = pd.DataFrame(chart_bars)
        df_indicators = compute_indicators(df)
        
        # Replace NaN values with None for JSON serialization
        records = df_indicators.where(pd.notnull(df_indicators), None).to_dict(orient="records")

        return {"ticker": ticker, "period": period, "interval": interval, "bars": records}
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
        return {"ticker": ticker, "pros_cons": profile["pros_cons"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
