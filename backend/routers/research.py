from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from services.data_fetcher import get_company_financials, get_company_profile
from services.pseudo_brain import get_company_research_notes
from services.research_audit import audit_research
from services.research_workflow import cached_research, ensure_research, start_research

router = APIRouter(tags=["research"])


class ResearchCollectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_urls: list[HttpUrl] = Field(default_factory=list, max_length=3)
    context_urls: list[HttpUrl] = Field(default_factory=list, max_length=3)


@router.get("/api/companies/{ticker}/research-workflow")
def get_research_workflow(ticker: str):
    return ensure_research(get_company_profile(ticker))


@router.post("/api/companies/{ticker}/research-workflow", status_code=202)
def collect_company_research(ticker: str, request: ResearchCollectionRequest):
    return start_research(
        get_company_profile(ticker),
        [str(url) for url in request.source_urls],
        force=True,
        context_urls=[str(url) for url in request.context_urls],
    )


@router.get("/api/companies/{ticker}/research-audit")
def get_research_audit(ticker: str):
    profile = get_company_profile(ticker)
    return audit_research(
        cached_research(profile["ticker"]), get_company_financials(profile["ticker"])
    )


@router.get("/api/companies/{ticker}/research-notes")
def get_research_notes(ticker: str):
    try:
        notes = get_company_research_notes(ticker)
        return notes
    except Exception as e:
        raise HTTPException(status_code=500, detail="Research data temporarily unavailable.") from e


@router.get("/api/companies/{ticker}/documents")
def get_documents(ticker: str):
    research = ensure_research(get_company_profile(ticker))
    return {
        "ticker": research["ticker"],
        "status": research["status"],
        "documents": [
            {k: v for k, v in document.items() if k not in {"passages", "relationships"}}
            for document in research["documents"]
        ],
    }


@router.get("/api/companies/{ticker}/insider-activity")
def get_insider_activity(ticker: str):
    symbol_bare = ticker.upper().replace(".NS", "").replace(".BO", "")
    return {
        "ticker": ticker,
        "insider_transactions": [],
        "source_url": f"https://www.nseindia.com/companies-listing/corporate-filings-insider-disclosures?symbol={symbol_bare}",
        "data_source": "unavailable",
        "message": "Insider disclosure feed is not connected. An empty list does not mean no transactions occurred.",
    }


@router.get("/api/leaderboard")
def get_strategy_leaderboard():
    return {
        "leaderboard": [],
        "message": "No community backtest strategies published yet.",
    }


@router.get("/api/keepalive")
def keepalive_cron():
    return {
        "status": "active",
        "message": "Keep-alive ping successful.",
        "timestamp": "live",
    }
