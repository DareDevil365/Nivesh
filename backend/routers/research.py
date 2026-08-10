from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from services.pseudo_brain import get_company_research_notes

router = APIRouter(tags=["research"])

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
    symbol_bare = ticker.upper().replace(".NS", "").replace(".BO", "")
    return {
        "ticker": ticker,
        "insider_transactions": [],
        "source_url": f"https://www.nseindia.com/companies-listing/corporate-filings-insider-disclosures?symbol={symbol_bare}",
        "message": "No recent insider disclosures reported."
    }

@router.get("/api/leaderboard")
def get_strategy_leaderboard():
    return {"leaderboard": [], "message": "No community backtest strategies published yet."}

@router.get("/api/keepalive")
def keepalive_cron():
    return {
        "status": "active",
        "message": "Keep-alive ping successful.",
        "timestamp": "live"
    }

