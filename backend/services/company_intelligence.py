"""Provider business context and capability state for the optional AI deep dive."""

from config import settings
from services.cache_manager import cache_manager
from services.data_fetcher import get_company_profile
from services.deep_dive import SECTIONS, cache_key
from services.research_workflow import cached_research


def get_company_intelligence(ticker, profile=None):
    p = profile or get_company_profile(ticker)
    return {
        "ticker": p["ticker"],
        "name": p["name"],
        "what_it_does": p.get("about"),
        "data_source": "provider_summary",
        "source_url": p["source_url"],
        "fetched_at": p.get("fetched_at"),
        "sector": p["sector"],
        "industry": p["industry"],
        "revenue_segments": [],
        "geographies": [],
        "key_risks": [],
        "tailwinds": [],
        "history": None,
        "management_vision": None,
        "ai_available": bool(settings.GEMINI_API_KEYS.strip()),
        "filings_available": len(cached_research(p["ticker"])["documents"]),
        "deep_dive": cache_manager.get(cache_key(p)),
        "sections": [{"id": key, "title": title} for key, title in SECTIONS.items()],
        "message": "AI reads the provider description, passages from collected company reports and any excerpt you add. It separates evidence from hypotheses and flags unanswered questions. Scripts collect sources and calculate financial inputs; AI does not invent missing figures.",
    }
