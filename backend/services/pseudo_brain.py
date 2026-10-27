"""Numeric threshold checks and official filing destinations; no fabricated document feed."""

from services.data_fetcher import get_company_profile, normalize_ticker
from services.snowflake_calculator import generate_pros_and_cons


def classify_filing_by_triage_rules(title):
    text = title.lower()
    for category, words in [
        ("Financial Results", ["financial result", "quarterly result"]),
        ("Board Meeting", ["board meeting"]),
        ("Credit Rating", ["credit rating"]),
        ("Auditor Change", ["auditor"]),
        ("Related Party Transaction", ["related party"]),
        ("Litigation & Regulatory", ["litigation", "penalty", "sebi"]),
        ("Pledge Change", ["pledge", "encumbrance"]),
    ]:
        if any(word in text for word in words):
            return category
    return "General Corporate"


def get_company_research_notes(ticker):
    symbol = normalize_ticker(ticker)
    bare = symbol.rsplit(".", 1)[0]
    profile = get_company_profile(symbol)
    pros, cons = generate_pros_and_cons(profile)
    flags = [
        {
            "type": "numeric_check",
            "label": "Threshold strength" if status == "positive" else "Caution flag",
            "text": item["text"],
            "status": status,
        }
        for items, status in ((pros, "positive"), (cons, "negative"))
        for item in items
    ]
    url = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
    return {
        "ticker": symbol,
        "symbol_bare": bare,
        "announcements": [],
        "concall_digest": {
            "covered": False,
            "quarter": None,
            "management_tone": None,
            "key_takeaways": [],
            "source_url": url,
            "message": "Transcript feed not connected.",
        },
        "official_exchange_filings_url": url,
        "bse_announcements_url": "https://www.bseindia.com/corporates/ann.html",
        "rule_based_flags": flags,
        "ai_derived_flags": [],
        "data_source": "numeric_checks",
        "fetched_at": profile.get("fetched_at"),
    }
