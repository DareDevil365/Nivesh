import logging
from typing import Dict, Any, List, Optional
from services.data_fetcher import get_company_profile

logger = logging.getLogger(__name__)

ANNOUNCEMENT_CATEGORIES = [
    "Financial Results", "Board Meeting", "Credit Rating",
    "Auditor Resignation", "Related Party Transaction",
    "Litigation & Regulatory", "Pledge Change",
    "Key Personnel Change", "General Corporate",
]


def classify_filing_by_triage_rules(title: str) -> str:
    """Rule-based keyword triage classifier — zero LLM cost."""
    t = title.lower()
    if any(k in t for k in ["financial result", "quarterly result", "audited result", "unaudited result"]):
        return "Financial Results"
    if any(k in t for k in ["board meeting", "notice of board"]):
        return "Board Meeting"
    if any(k in t for k in ["credit rating", "rating upgrade", "rating downgrade", "rating reaffirm"]):
        return "Credit Rating"
    if "auditor" in t and any(k in t for k in ["resign", "change", "appointment"]):
        return "Auditor Resignation"
    if "related party" in t:
        return "Related Party Transaction"
    if any(k in t for k in ["litigation", "court", "sebi", "penalty", "show cause", "adjudication"]):
        return "Litigation & Regulatory"
    if any(k in t for k in ["pledge", "encumbrance"]):
        return "Pledge Change"
    if any(k in t for k in ["appointment", "resignation", "ceo", "cfo", "md ", "director"]):
        return "Key Personnel Change"
    return "General Corporate"


def get_company_research_notes(ticker: str) -> Dict[str, Any]:
    """
    Returns the Research Digest for a company.

    Data contract (honest):
    - rule_based_flags: Computed from real numeric fundamentals (no LLM).
    - ai_derived_flags: Empty unless a real Gemini call succeeds.
    - announcements: Empty — fetching from NSE filing API requires authenticated session.
    - concall_digest: Not covered unless a real transcript source is connected.

    The frontend is responsible for showing clear "unavailable" states rather than
    fake placeholder data.
    """
    ticker_clean = ticker.upper().strip()
    symbol_bare = ticker_clean.replace(".NS", "").replace(".BO", "")

    rule_based_flags: List[Dict[str, Any]] = []

    # ── Compute flags from real numeric profile ──
    try:
        profile = get_company_profile(ticker_clean)

        debt_eq = profile.get("debt_equity")
        if debt_eq is not None:
            if debt_eq == 0.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Debt Status",
                    "text": "Company is virtually debt-free (D/E = 0.0)", "status": "positive"
                })
            elif debt_eq < 0.3:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Debt Coverage",
                    "text": f"Healthy leverage with D/E ratio at {debt_eq:.2f}", "status": "positive"
                })
            elif debt_eq > 1.5:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Debt Risk",
                    "text": f"Elevated debt-to-equity ratio of {debt_eq:.2f}x — above safe threshold", "status": "negative"
                })

        promoter = profile.get("promoter_holding")
        if promoter is not None:
            if promoter > 60.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Promoter Holding",
                    "text": f"Strong insider conviction — promoter holding at {promoter:.1f}%", "status": "positive"
                })
            elif promoter < 25.0 and promoter > 0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Promoter Holding",
                    "text": f"Low promoter confidence — holding at {promoter:.1f}%", "status": "negative"
                })

        pe = profile.get("pe")
        pb = profile.get("pb")
        if pe is not None:
            if pe < 15.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Valuation",
                    "text": f"Attractive valuation at P/E of {pe:.1f}x — below market median", "status": "positive"
                })
            elif pe > 50.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Valuation",
                    "text": f"Premium valuation — P/E of {pe:.1f}x prices in high growth expectations", "status": "neutral"
                })

        roe = profile.get("roe")
        if roe is not None:
            if roe > 20.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Return Quality",
                    "text": f"Outstanding capital efficiency — ROE of {roe:.1f}%", "status": "positive"
                })
            elif roe < 8.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Return Quality",
                    "text": f"Below-average ROE of {roe:.1f}% — low returns on shareholder capital", "status": "negative"
                })

        interest_cov = profile.get("interest_coverage")
        if interest_cov is not None:
            if interest_cov > 5.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Interest Coverage",
                    "text": f"Strong interest coverage of {interest_cov:.1f}x — debt servicing comfortable", "status": "positive"
                })
            elif interest_cov < 2.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Interest Coverage",
                    "text": f"Weak interest coverage of {interest_cov:.1f}x — potential debt stress", "status": "negative"
                })

        div_yield = profile.get("div_yield", 0)
        if div_yield and div_yield > 3.0:
            rule_based_flags.append({
                "type": "numeric_check", "label": "Dividend",
                "text": f"Generous dividend yield of {div_yield:.1f}% — income-friendly stock", "status": "positive"
            })

        current_ratio = profile.get("current_ratio")
        if current_ratio is not None:
            if current_ratio < 1.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Liquidity",
                    "text": f"Current ratio below 1.0 ({current_ratio:.2f}x) — short-term liquidity concern", "status": "negative"
                })
            elif current_ratio > 2.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Liquidity",
                    "text": f"Strong current ratio of {current_ratio:.2f}x — healthy short-term liquidity", "status": "positive"
                })

        # Revenue growth trend
        rev_growth = profile.get("revenue_growth_3yr")
        if rev_growth is not None:
            if rev_growth > 15.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Revenue Growth",
                    "text": f"Strong revenue CAGR of {rev_growth:.1f}% — top-line momentum intact", "status": "positive"
                })
            elif rev_growth < 0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Revenue Trend",
                    "text": f"Revenue shrinking at {rev_growth:.1f}% — investigate structural demand headwinds", "status": "negative"
                })

        # ROCE vs ROE divergence (earnings quality signal)
        if roe is not None and roce is not None and roe > 0 and roce > 0:
            divergence = roe - roce
            if divergence > 12.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Earnings Quality",
                    "text": f"ROE ({roe:.1f}%) significantly exceeds ROCE ({roce:.1f}%) — may signal high financial leverage inflating returns", "status": "neutral"
                })
            elif roe > 18.0 and roce > 18.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Earnings Quality",
                    "text": f"Both ROE ({roe:.1f}%) and ROCE ({roce:.1f}%) above 18% — genuinely high-quality returns business", "status": "positive"
                })

        # EPS growth momentum
        eps_growth = profile.get("eps_growth_3yr")
        if eps_growth is not None:
            if eps_growth > 20.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "EPS Growth",
                    "text": f"EPS compounding at {eps_growth:.1f}% — strong earnings per share momentum", "status": "positive"
                })
            elif eps_growth < -5.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "EPS Growth",
                    "text": f"Declining EPS growth of {eps_growth:.1f}% — profitability per share is eroding", "status": "negative"
                })

        # Payout ratio sustainability
        payout = profile.get("payout_ratio")
        if payout is not None and payout > 0:
            if payout > 80.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Dividend Sustainability",
                    "text": f"Payout ratio of {payout:.0f}% — dividend may be unsustainable if earnings slip", "status": "neutral"
                })
            elif payout > 0 and payout <= 50.0 and div_yield and div_yield > 1.0:
                rule_based_flags.append({
                    "type": "numeric_check", "label": "Dividend Sustainability",
                    "text": f"Healthy payout ratio of {payout:.0f}% with {div_yield:.1f}% yield — dividend appears well-covered", "status": "positive"
                })

    except Exception as e:
        logger.warning(f"Could not load profile for research flags ({ticker}): {e}")

    nse_url = f"https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol={symbol_bare}"
    bse_url = f"https://www.bseindia.com/corporates/ann.html?scripcd={symbol_bare}&qtrid=99"

    return {
        "ticker": ticker_clean,
        "symbol_bare": symbol_bare,
        "announcements": [],
        "concall_digest": {
            "covered": False,
            "quarter": None,
            "management_tone": None,
            "key_takeaways": [],
            "source_url": nse_url,
            "message": "Live concall transcript data requires a real-time filing integration. View official transcripts on NSE India."
        },
        "official_exchange_filings_url": nse_url,
        "bse_announcements_url": bse_url,
        "rule_based_flags": rule_based_flags,
        "ai_derived_flags": [],
        "data_source": "rule_based" if rule_based_flags else "unavailable",
    }
