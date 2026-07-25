import hashlib
from typing import Dict, Any, List, Optional

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
    Handles ~80% of routine corporate announcements.
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

def get_company_research_notes(ticker: str) -> Dict[str, Any]:
    """
    Returns AI Research Digest notes for a company.
    Strictly separates rule-based numerical checks from qualitative document summaries.
    Every AI summary line carries a direct link to the source document.
    """
    ticker_clean = ticker.upper().strip()

    # Sample announcements & documents feed with direct source URLs
    announcements = [
        {
            "id": "doc-1",
            "date": "2026-07-20",
            "title": "Un-audited Financial Results for Q1 FY27 & Press Release",
            "category": "Financial Results",
            "summary_text": "Management reported steady top-line expansion led by strong retail and digital services growth.",
            "source_url": f"https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol={ticker_clean.replace('.NS','')}",
            "ai_summarized": True
        },
        {
            "id": "doc-2",
            "date": "2026-07-02",
            "title": "Intimation of CRISIL AAA/Stable Credit Rating Reaffirmation",
            "category": "Credit Rating",
            "summary_text": "CRISIL reaffirmed AAA credit rating with stable outlook citing robust balance sheet liquidity.",
            "source_url": f"https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol={ticker_clean.replace('.NS','')}",
            "ai_summarized": False
        },
        {
            "id": "doc-3",
            "date": "2026-06-15",
            "title": "Outcome of Board Meeting held on June 15, 2026",
            "category": "Board Meeting",
            "summary_text": "Board approved capital expenditure plan for expansion into clean energy infrastructure.",
            "source_url": f"https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol={ticker_clean.replace('.NS','')}",
            "ai_summarized": True
        }
    ]

    concall_digest = {
        "covered": True,
        "quarter": "Q1 FY27",
        "management_tone": "Confident",
        "key_takeaways": [
            "Guidance maintained: Double-digit revenue growth projected for full fiscal year.",
            "Margin expansion: Operating margins improved 40bps quarter-on-quarter due to operating leverage.",
            "CapEx roadmap: New capacity commissioning remains on schedule for Q3."
        ],
        "source_url": f"https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol={ticker_clean.replace('.NS','')}"
    }

    # Quality/Red Flags panel: Clearly distinguishing rule-based vs AI-derived
    rule_based_flags = [
        {"type": "numeric_check", "label": "Debt Coverage", "text": "Interest coverage ratio is healthy at > 5.0x", "status": "positive"},
        {"type": "numeric_check", "label": "Pledge Status", "text": "Zero promoter shares pledged", "status": "positive"}
    ]

    ai_derived_flags = [
        {"type": "ai_document_flag", "label": "Management Tone", "text": "Management expressed optimism regarding demand recovery in concall Q&A", "status": "positive"}
    ]

    return {
        "ticker": ticker_clean,
        "announcements": announcements,
        "concall_digest": concall_digest,
        "rule_based_flags": rule_based_flags,
        "ai_derived_flags": ai_derived_flags
    }
