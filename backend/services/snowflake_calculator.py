from typing import Dict, Any

def compute_snowflake_scores(fundamentals: Dict[str, Any]) -> Dict[str, int]:
    """
    Computes deterministic Simplywall.st-style 5-axis Snowflake Scores (0-6 for each axis)
    based on raw numeric fundamental ratios. Zero LLM involvement.
    """
    pe = fundamentals.get("pe", 25.0)
    pb = fundamentals.get("pb", 3.5)
    roe = fundamentals.get("roe", 14.0)
    roce = fundamentals.get("roce", 16.0)
    debt_equity = fundamentals.get("debt_equity", 0.4)
    div_yield = fundamentals.get("div_yield", 1.2)
    rev_growth = fundamentals.get("revenue_growth_3yr", 12.0)
    eps_growth = fundamentals.get("eps_growth_3yr", 15.0)
    pledged = fundamentals.get("pledged_shares_pct", 0.0)

    # 1. Value (0-6)
    v_score = 0
    if pe < 25.0: v_score += 1
    if pe < 15.0: v_score += 1
    if pb < 4.0: v_score += 1
    if pb < 2.0: v_score += 1
    if div_yield > 1.0: v_score += 1
    if rev_growth > 10.0: v_score += 1

    # 2. Future (0-6)
    f_score = 0
    if rev_growth > 8.0: f_score += 1
    if rev_growth > 18.0: f_score += 1
    if eps_growth > 10.0: f_score += 1
    if eps_growth > 20.0: f_score += 1
    if roe > 15.0: f_score += 1
    if roce > 15.0: f_score += 1

    # 3. Past (0-6)
    p_score = 0
    if roe > 12.0: p_score += 1
    if roe > 20.0: p_score += 1
    if roce > 15.0: p_score += 1
    if eps_growth > 10.0: p_score += 1
    if rev_growth > 10.0: p_score += 1
    if debt_equity < 0.8: p_score += 1

    # 4. Health (0-6)
    h_score = 0
    if debt_equity < 0.5: h_score += 1
    if debt_equity < 0.1: h_score += 1  # Net debt free
    if pledged < 5.0: h_score += 1
    if pledged == 0.0: h_score += 1
    if roce > 12.0: h_score += 1
    if roe > 10.0: h_score += 1

    # 5. Dividend (0-6)
    d_score = 0
    if div_yield > 0.5: d_score += 1
    if div_yield > 1.5: d_score += 1
    if div_yield > 3.0: d_score += 1
    if roe > 15.0: d_score += 1  # Affordable dividend
    if debt_equity < 0.5: d_score += 1
    if eps_growth > 5.0: d_score += 1

    return {
        "value": min(6, max(0, v_score)),
        "future": min(6, max(0, f_score)),
        "past": min(6, max(0, p_score)),
        "health": min(6, max(0, h_score)),
        "dividend": min(6, max(0, d_score))
    }

def generate_rule_based_pros_cons(fundamentals: Dict[str, Any]) -> Dict[str, list]:
    """
    Generates rule-based Screener.in-style Pros and Cons flags directly from numbers.
    Zero LLM involvement.
    """
    pros = []
    cons = []

    debt_eq = fundamentals.get("debt_equity", 0.0)
    roe = fundamentals.get("roe", 0.0)
    roce = fundamentals.get("roce", 0.0)
    pe = fundamentals.get("pe", 0.0)
    div_yield = fundamentals.get("div_yield", 0.0)
    rev_growth = fundamentals.get("revenue_growth_3yr", 0.0)
    pledged = fundamentals.get("pledged_shares_pct", 0.0)
    promoter = fundamentals.get("promoter_holding", 0.0)

    if debt_eq < 0.1:
        pros.append({"text": "Company is virtually debt-free", "rule_id": "DEBT_FREE"})
    elif debt_eq < 0.5:
        pros.append({"text": "Company maintains a healthy debt-to-equity ratio", "rule_id": "HEALTHY_DEBT"})
    else:
        cons.append({"text": f"High debt to equity ratio of {debt_eq:.2f}", "rule_id": "HIGH_DEBT"})

    if roe > 20.0:
        pros.append({"text": f"Good track record of Return on Equity (ROE): 3yr ROE {roe:.1f}%", "rule_id": "HIGH_ROE"})
    elif roe < 10.0:
        cons.append({"text": f"Low Return on Equity of {roe:.1f}%", "rule_id": "LOW_ROE"})

    if roce > 20.0:
        pros.append({"text": f"Strong Return on Capital Employed (ROCE): {roce:.1f}%", "rule_id": "HIGH_ROCE"})

    if div_yield > 2.0:
        pros.append({"text": f"Offers a good dividend yield of {div_yield:.2f}%", "rule_id": "GOOD_DIVIDEND"})

    if pledged > 5.0:
        cons.append({"text": f"Promoter pledged shares are significant ({pledged:.1f}%)", "rule_id": "PLEDGED_SHARES"})

    if promoter > 50.0:
        pros.append({"text": f"High promoter holding of {promoter:.1f}%", "rule_id": "HIGH_PROMOTER"})
    elif promoter < 30.0 and promoter > 0:
        cons.append({"text": f"Low promoter holding of {promoter:.1f}%", "rule_id": "LOW_PROMOTER"})

    if pe > 40.0:
        cons.append({"text": f"Stock is trading at a high valuation P/E of {pe:.1f}x", "rule_id": "HIGH_PE"})

    return {"pros": pros, "cons": cons}
