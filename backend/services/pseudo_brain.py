import hashlib
import logging
from typing import Dict, Any, List, Optional
import httpx
from services.gemini_client import gemini_rotator

logger = logging.getLogger(__name__)

ANNOUNCEMENT_CATEGORIES = [
    "Financial Results",
    "Board Meeting",
    "Credit Rating",
    "Auditor Resignation",
    "Related Party Transaction",
    "Litigation & Regulatory",
    "Pledge Change",
    "Key Personnel Change",
    "General Corporate"
]

def classify_filing_by_triage_rules(title: str) -> str:
    """
    Rule-based keyword triage classifier (no LLM, 0 cost).
    Handles routine corporate announcements cleanly.
    """
    title_lower = title.lower()
    if "financial result" in title_lower or "quarterly result" in title_lower or "audited result" in title_lower:
        return "Financial Results"
    if "board meeting" in title_lower or "notice of board" in title_lower:
        return "Board Meeting"
    if "credit rating" in title_lower or "rating upgrade" in title_lower or "rating downgrade" in title_lower:
        return "Credit Rating"
    if "auditor" in title_lower and ("resign" in title_lower or "change" in title_lower):
        return "Auditor Resignation"
    if "related party" in title_lower:
        return "Related Party Transaction"
    if "litigation" in title_lower or "court" in title_lower or "sebi" in title_lower or "penalty" in title_lower:
        return "Litigation & Regulatory"
    if "pledge" in title_lower or "encumbrance" in title_lower:
        return "Pledge Change"
    if "appointment" in title_lower or "resignation" in title_lower or "ceo" in title_lower or "cfo" in title_lower:
        return "Key Personnel Change"
    return "General Corporate"

def summarize_filing_with_gemini(title: str, category: str) -> str:
    """Uses Gemini API rotator to generate a 1-sentence synthesis for high-signal filings."""
    active_key = gemini_rotator.get_active_key(task_type="heavy")
    if not active_key:
        return f"{category} filing submitted to exchange."

    try:
        prompt = f"Summarize this corporate filing title into 1 clear, professional sentence for investors: '{title}'. Return raw text only."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={active_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        with httpx.Client(timeout=4.0) as client:
            res = client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    summary = candidates[0]["content"]["parts"][0]["text"].strip()
                    gemini_rotator.report_success(active_key)
                    return summary
            gemini_rotator.report_error(active_key, status_code=res.status_code)
    except Exception as e:
        logger.warning(f"Gemini filing summary failed ({e}). Returning fallback text.")

    return f"Official {category} filing submitted to exchange."

import logging
from typing import Dict, Any, List, Optional
import httpx
from services.data_fetcher import get_company_profile
from services.gemini_client import gemini_rotator

logger = logging.getLogger(__name__)

ANNOUNCEMENT_CATEGORIES = [
    "Financial Results",
    "Board Meeting",
    "Credit Rating",
    "Auditor Resignation",
    "Related Party Transaction",
    "Litigation & Regulatory",
    "Pledge Change",
    "Key Personnel Change",
    "General Corporate"
]

def get_company_research_notes(ticker: str) -> Dict[str, Any]:
    """
    Returns Research Digest notes for a company using real fundamental data & direct exchange filing links.
    Does NOT invent fake concall transcripts or hardcoded sample filings.
    """
    ticker_clean = ticker.upper().strip()
    symbol_bare = ticker_clean.replace(".NS", "").replace(".BO", "")

    # Try fetching profile to generate real numeric flags
    rule_based_flags = []
    try:
        profile = get_company_profile(ticker_clean)
        debt_eq = profile.get("debt_equity")
        if debt_eq is not None:
            if debt_eq == 0.0:
                rule_based_flags.append({"type": "numeric_check", "label": "Debt Coverage", "text": "Company is virtually debt-free (D/E = 0.0)", "status": "positive"})
            elif debt_eq < 0.5:
                rule_based_flags.append({"type": "numeric_check", "label": "Debt Coverage", "text": f"Healthy leverage with D/E ratio at {debt_eq:.2f}", "status": "positive"})
            elif debt_eq > 1.2:
                rule_based_flags.append({"type": "numeric_check", "label": "Debt Risk", "text": f"Elevated debt-to-equity ratio of {debt_eq:.2f}", "status": "negative"})

        promoter = profile.get("promoter_holding")
        if promoter is not None:
            if promoter > 60.0:
                rule_based_flags.append({"type": "numeric_check", "label": "Promoter Holding", "text": f"Strong insider holding at {promoter:.1f}%", "status": "positive"})
            elif promoter < 30.0 and promoter > 0:
                rule_based_flags.append({"type": "numeric_check", "label": "Promoter Holding", "text": f"Low promoter holding at {promoter:.1f}%", "status": "negative"})

        pe = profile.get("pe")
        if pe is not None:
            if pe > 35.0:
                rule_based_flags.append({"type": "numeric_check", "label": "Valuation Multiples", "text": f"Trading at elevated P/E ratio of {pe:.1f}x", "status": "negative"})
            elif pe < 20.0:
                rule_based_flags.append({"type": "numeric_check", "label": "Valuation Multiples", "text": f"Attractive P/E ratio of {pe:.1f}x", "status": "positive"})

    except Exception as e:
        logger.warning(f"Could not load real profile for research flags: {e}")

    nse_filings_url = f"https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol={symbol_bare}"

    return {
        "ticker": ticker_clean,
        "announcements": [],
        "concall_digest": {
            "covered": False,
            "quarter": None,
            "management_tone": "N/A",
            "key_takeaways": [],
            "source_url": nse_filings_url,
            "message": "Official earnings conference call digest unavailable from exchange feed."
        },
        "official_exchange_filings_url": nse_filings_url,
        "rule_based_flags": rule_based_flags,
        "ai_derived_flags": []
    }

