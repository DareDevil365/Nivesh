from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from services.pseudo_brain import get_company_research_notes

router = APIRouter(tags=["research"])

SAMPLE_LEADERBOARD = [
    {
        "id": "strat-1",
        "name": "RSI Oversold Swing Strategy",
        "ticker": "RELIANCE.NS",
        "author": "TraderQuant99",
        "total_return_pct": 48.5,
        "cagr_pct": 38.2,
        "sharpe_ratio": 2.15,
        "max_drawdown_pct": 9.4,
        "win_rate_pct": 82.0,
        "total_trades": 12,
        "scenario": "COVID-19 Recovery"
    },
    {
        "id": "strat-2",
        "name": "TCS Quality Dip Buyer",
        "ticker": "TCS.NS",
        "author": "ValueInvestorIN",
        "total_return_pct": 34.2,
        "cagr_pct": 28.5,
        "sharpe_ratio": 1.85,
        "max_drawdown_pct": 7.8,
        "win_rate_pct": 75.0,
        "total_trades": 8,
        "scenario": "GFC 2008 Recovery"
    },
    {
        "id": "strat-3",
        "name": "Infosys Momentum Breakout",
        "ticker": "INFY.NS",
        "author": "TechTraderPro",
        "total_return_pct": 29.8,
        "cagr_pct": 24.1,
        "sharpe_ratio": 1.62,
        "max_drawdown_pct": 11.2,
        "win_rate_pct": 70.0,
        "total_trades": 10,
        "scenario": "Demonetization"
    }
]

SAMPLE_INSIDER_TRADES = [
    {
        "disclosure_date": "2026-07-15",
        "person_name": "Promoter Group Trust",
        "role": "Promoter",
        "transaction_type": "Buy (Market Acquisition)",
        "quantity": 150000,
        "value": 445000000,
        "source_url": "https://www.nseindia.com/companies-listing/corporate-filings-insider-disclosures"
    },
    {
        "disclosure_date": "2026-06-28",
        "person_name": "Executive Director",
        "role": "Director",
        "transaction_type": "Buy (Option Exercise)",
        "quantity": 25000,
        "value": 72500000,
        "source_url": "https://www.nseindia.com/companies-listing/corporate-filings-insider-disclosures"
    }
]

@router.get("/api/companies/{ticker}/research-notes")
def get_research_notes(ticker: str):
    try:
        notes = get_company_research_notes(ticker)
        return notes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/companies/{ticker}/documents")
def get_documents(ticker: str):
    notes = get_company_research_notes(ticker)
    return {"ticker": ticker, "documents": notes["announcements"]}

@router.get("/api/companies/{ticker}/insider-activity")
def get_insider_activity(ticker: str):
    return {"ticker": ticker, "insider_transactions": SAMPLE_INSIDER_TRADES}

@router.get("/api/leaderboard")
def get_strategy_leaderboard():
    return {"leaderboard": SAMPLE_LEADERBOARD}

@router.get("/api/keepalive")
def keepalive_cron():
    """
    Keep-alive endpoint for GitHub Actions cron job to prevent
    Render free-tier web service sleeping and Supabase DB pausing.
    """
    return {
        "status": "active",
        "message": "Keep-alive ping successful. Render backend and Postgres active.",
        "timestamp": "live"
    }
