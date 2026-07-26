from typing import Dict, Any, List, Tuple

def compute_snowflake_scores(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Computes SimplyWall.St-accurate 30-Check Binary Scoring Engine (0-6 per axis).
    
    Each axis gets exactly 6 checks (pass=1, fail=0).
    Non-dividend stocks score 0/6 on Dividend (correct, not inflated).
    """
    pe = data.get("pe", 25.0) or 25.0
    pb = data.get("pb", 3.5) or 3.5
    roe = data.get("roe", 14.0) or 14.0
    roce = data.get("roce", 16.0) or 16.0
    debt_equity = data.get("debt_equity", 0.4) or 0.4
    div_yield = data.get("div_yield", 0.0) or 0.0
    rev_growth = data.get("revenue_growth_3yr", 12.0) or 12.0
    eps_growth = data.get("eps_growth_3yr", 15.0) or 15.0
    operating_cf_debt = data.get("operating_cf_debt_ratio", 0.35) or 0.35
    current_ratio = data.get("current_ratio", 1.4) or 1.4
    interest_coverage = data.get("interest_coverage", 4.5) or 4.5
    
    sector_pe = data.get("sector_median_pe", 28.0) or 28.0
    sector_pb = data.get("sector_median_pb", 4.0) or 4.0
    market_pe = 22.0  # Nifty 50 median P/E baseline
    
    # ----------------------------------------------------
    # 1. VALUE AXIS (0-6 checks)
    # ----------------------------------------------------
    val_score = 0
    if pe < sector_pe: val_score += 1             # Check 1: P/E < sector median
    if pb < sector_pb: val_score += 1             # Check 2: P/B < sector median
    if pe < market_pe: val_score += 1             # Check 3: P/E < Nifty median
    peg = pe / max(1.0, eps_growth)
    if peg < 1.0: val_score += 1                  # Check 4: PEG < 1.0
    if pb < 3.0: val_score += 1                   # Check 5: Reasonable P/B (<3.0)
    if pe < 20.0: val_score += 1                  # Check 6: Deep value P/E (<20.0)

    # ----------------------------------------------------
    # 2. FUTURE GROWTH AXIS (0-6 checks)
    # ----------------------------------------------------
    fut_score = 0
    if rev_growth > 10.0: fut_score += 1          # Check 1: Revenue growth > 10%
    if eps_growth > 12.0: fut_score += 1          # Check 2: EPS growth > 12%
    if rev_growth > 20.0: fut_score += 1          # Check 3: High revenue growth (>20%)
    if eps_growth > 20.0: fut_score += 1          # Check 4: High EPS growth (>20%)
    if roe > 18.0: fut_score += 1                 # Check 5: Forward ROE capacity (>18%)
    if rev_growth > 0 and eps_growth > 0: fut_score += 1 # Check 6: Consistent growth trend

    # ----------------------------------------------------
    # 3. PAST PERFORMANCE AXIS (0-6 checks)
    # ----------------------------------------------------
    past_score = 0
    if eps_growth > 0: past_score += 1            # Check 1: Positive trailing 5yr growth
    if eps_growth > rev_growth: past_score += 1   # Check 2: Margin expansion (EPS > Rev growth)
    if roe > 15.0: past_score += 1                # Check 3: High ROE (>15%)
    if roce > 15.0: past_score += 1               # Check 4: High ROCE (>15%)
    if roe > 20.0: past_score += 1                # Check 5: Top-tier ROE (>20%)
    if roce > 20.0: past_score += 1               # Check 6: Top-tier ROCE (>20%)

    # ----------------------------------------------------
    # 4. FINANCIAL HEALTH AXIS (0-6 checks)
    # ----------------------------------------------------
    health_score = 0
    if current_ratio >= 1.0: health_score += 1    # Check 1: Short-term liquidity (Current Ratio >= 1)
    if debt_equity < 1.0: health_score += 1       # Check 2: D/E < 1.0
    if debt_equity < 0.5: health_score += 1       # Check 3: Low debt (D/E < 0.5)
    if debt_equity == 0.0: health_score += 1      # Check 4: Zero debt
    if operating_cf_debt > 0.20: health_score += 1# Check 5: Cash flow covers >20% debt
    if interest_coverage >= 3.0: health_score += 1# Check 6: Interest coverage >= 3x

    # ----------------------------------------------------
    # 5. DIVIDEND AXIS (0-6 checks)
    # ----------------------------------------------------
    div_score = 0
    if div_yield > 0.0:
        div_score += 1                            # Check 1: Pays a dividend
        if div_yield > 1.5: div_score += 1        # Check 2: Yield > 1.5% (notable)
        if div_yield > 3.0: div_score += 1        # Check 3: Yield > 3.0% (top tier)
        payout_ratio = data.get("payout_ratio", 40.0) or 40.0
        if payout_ratio < 80.0: div_score += 1    # Check 4: Sustainable payout (<80%)
        if payout_ratio < 50.0: div_score += 1    # Check 5: High coverage payout (<50%)
        if eps_growth > 0: div_score += 1         # Check 6: Dividend backed by EPS growth

    return {
        "value": float(val_score),
        "future": float(fut_score),
        "past": float(past_score),
        "health": float(health_score),
        "dividend": float(div_score),
        "total": float(val_score + fut_score + past_score + health_score + div_score)
    }

def generate_pros_and_cons(data: Dict[str, Any]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Generates Screener.in-style rule-based Pros and Cons (0 LLM reliance)."""
    pros = []
    cons = []
    
    pe = data.get("pe", 25.0) or 25.0
    pb = data.get("pb", 3.5) or 3.5
    roe = data.get("roe", 14.0) or 14.0
    roce = data.get("roce", 16.0) or 16.0
    debt_equity = data.get("debt_equity", 0.4) or 0.4
    div_yield = data.get("div_yield", 0.0) or 0.0
    rev_growth = data.get("revenue_growth_3yr", 12.0) or 12.0
    promoter_holding = data.get("promoter_holding", 50.0) or 50.0
    pledged_pct = data.get("pledged_shares_pct", 0.0) or 0.0
    interest_coverage = data.get("interest_coverage", 4.0) or 4.0

    # PROS
    if debt_equity == 0.0:
        pros.append({"text": "Company is virtually debt-free", "rule": "zero_debt"})
    elif debt_equity < 0.3:
        pros.append({"text": "Low debt-to-equity ratio", "rule": "low_debt"})
        
    if roe > 20.0:
        pros.append({"text": "Delivers outstanding Return on Equity (>20%)", "rule": "high_roe"})
    elif roe > 15.0:
        pros.append({"text": "Good Return on Equity (>15%) track record", "rule": "good_roe"})
        
    if roce > 20.0:
        pros.append({"text": "High Return on Capital Employed (>20%)", "rule": "high_roce"})
        
    if div_yield > 2.0:
        pros.append({"text": f"Healthy dividend yield of {div_yield:.1f}%", "rule": "good_dividend"})
        
    if rev_growth > 15.0:
        pros.append({"text": f"Strong 3-year revenue CAGR of {rev_growth:.1f}%", "rule": "high_growth"})

    if promoter_holding > 60.0:
        pros.append({"text": f"High promoter holding at {promoter_holding:.1f}%", "rule": "high_promoter"})

    # CONS
    if pe > 30.0:
        cons.append({"text": f"Trading at a high P/E multiple of {pe:.1f}x", "rule": "high_pe"})
        
    if pb > 6.0:
        cons.append({"text": f"High Price-to-Book value ratio of {pb:.1f}x", "rule": "high_pb"})

    if debt_equity > 1.2:
        cons.append({"text": f"Elevated debt-to-equity ratio of {debt_equity:.2f}", "rule": "high_debt"})
        
    if interest_coverage < 2.0:
        cons.append({"text": f"Low interest coverage ratio of {interest_coverage:.1f}x", "rule": "low_coverage"})
        
    if pledged_pct > 5.0:
        cons.append({"text": f"Promoter pledged shares stand at {pledged_pct:.1f}%", "rule": "pledged_risk"})

    if promoter_holding < 30.0 and promoter_holding > 0:
        cons.append({"text": f"Low promoter holding of {promoter_holding:.1f}%", "rule": "low_promoter"})

    if div_yield == 0.0:
        cons.append({"text": "Company does not currently pay a dividend", "rule": "no_dividend"})

    return pros, cons
