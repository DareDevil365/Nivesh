from typing import Any, Dict, List, Tuple


def compute_snowflake_scores(data):
    def metric(key):
        return data.get(key)

    pe, pb, roe, roce, debt, dy = (
        metric(k) for k in ("pe", "pb", "roe", "roce", "debt_equity", "div_yield")
    )
    rev, eps, cf, liquidity, interest, payout = (
        metric(k)
        for k in (
            "revenue_growth_3yr",
            "eps_growth_3yr",
            "operating_cf_debt_ratio",
            "current_ratio",
            "interest_coverage",
            "payout_ratio",
        )
    )

    def check(label, value, predicate):
        return {
            "label": label,
            "available": value is not None,
            "passed": bool(predicate(value)) if value is not None else None,
        }

    axes = {
        "value": [
            check("Positive P/E below 20", pe, lambda x: 0 < x < 20),
            check("Positive P/E below 30", pe, lambda x: 0 < x < 30),
            check("Positive P/B below 3", pb, lambda x: 0 < x < 3),
            check("Positive P/B below 5", pb, lambda x: 0 < x < 5),
            check(
                "PEG below 1 using three-year EPS CAGR",
                pe / eps if pe is not None and pe > 0 and eps and eps > 0 else None,
                lambda x: x < 1,
            ),
            check("Dividend yield above 2%", dy, lambda x: x > 2),
        ],
        "future": [
            check("Three-year revenue CAGR above 10%", rev, lambda x: x > 10),
            check("Revenue CAGR above 20%", rev, lambda x: x > 20),
            check("Three-year EPS CAGR above 10%", eps, lambda x: x > 10),
            check("EPS CAGR above 20%", eps, lambda x: x > 20),
            check("ROE above 18%", roe, lambda x: x > 18),
            check("ROCE above 18%", roce, lambda x: x > 18),
        ],
        "past": [
            check("Positive three-year revenue CAGR", rev, lambda x: x > 0),
            check("Positive three-year EPS CAGR", eps, lambda x: x > 0),
            check("ROE above 15%", roe, lambda x: x > 15),
            check("ROE above 20%", roe, lambda x: x > 20),
            check("ROCE above 15%", roce, lambda x: x > 15),
            check("ROCE above 20%", roce, lambda x: x > 20),
        ],
        "health": [
            check("Current ratio at least 1", liquidity, lambda x: x >= 1),
            check("Debt/equity below 1", debt, lambda x: 0 <= x < 1),
            check("Debt/equity below 0.5", debt, lambda x: 0 <= x < 0.5),
            check("Reported zero debt", debt, lambda x: x == 0),
            check("Operating cash flow/debt above 0.2", cf, lambda x: x > 0.2),
            check("Interest coverage at least 3", interest, lambda x: x >= 3),
        ],
        "dividend": [
            check("Pays a reported dividend", dy, lambda x: x > 0),
            check("Dividend yield above 1.5%", dy, lambda x: x > 1.5),
            check("Dividend yield above 3%", dy, lambda x: x > 3),
            check("Payout ratio between 0 and 80%", payout, lambda x: 0 < x < 80),
            check("Payout ratio between 0 and 50%", payout, lambda x: 0 < x < 50),
            check("Positive three-year EPS CAGR", eps, lambda x: x > 0),
        ],
    }
    if any(
        word in (data.get("sector", "") + " " + data.get("industry", "")).lower()
        for word in ("financial", "bank", "insurance")
    ) or data.get("instrument_type") in {"ETF", "MUTUALFUND"}:
        for axis in ("health",):
            for item in axes[axis]:
                item.update(available=False, passed=None)
    scores = {
        axis: float(sum(item["passed"] is True for item in checks)) for axis, checks in axes.items()
    }
    counts = {axis: sum(item["available"] for item in checks) for axis, checks in axes.items()}
    return {
        **scores,
        "total": sum(scores.values()),
        "data_confidence": {
            axis: "none" if n == 0 else "high" if n == 6 else "low" for axis, n in counts.items()
        },
        "available_checks": counts,
        "checks": axes,
        "methodology": "Fixed-threshold research checklist, not a price target, analyst forecast or investment recommendation. Missing checks do not pass. Growth refers to historical three-year CAGR; the growth axis is not a forecast. Health checks are not applied to financial institutions or funds.",
    }


def generate_pros_and_cons(
    data: Dict[str, Any],
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Generates Screener.in-style rule-based Pros and Cons from actual non-null data."""
    pros = []
    cons = []

    pe = data.get("pe")
    pb = data.get("pb")
    roe = data.get("roe")
    roce = data.get("roce")
    debt_equity = data.get("debt_equity")
    div_yield = data.get("div_yield")
    rev_growth = data.get("revenue_growth_3yr")
    promoter_holding = data.get("promoter_holding")
    pledged_pct = data.get("pledged_shares_pct")
    interest_coverage = data.get("interest_coverage")

    # PROS
    if debt_equity is not None:
        if debt_equity == 0.0:
            pros.append({"text": "Company is virtually debt-free", "rule_id": "zero_debt"})
        elif debt_equity < 0.3:
            pros.append(
                {
                    "text": f"Low debt-to-equity ratio of {debt_equity:.2f}",
                    "rule_id": "low_debt",
                }
            )

    if roe is not None:
        if roe > 20.0:
            pros.append(
                {
                    "text": f"Delivers outstanding Return on Equity ({roe:.1f}%)",
                    "rule_id": "high_roe",
                }
            )
        elif roe > 15.0:
            pros.append(
                {
                    "text": f"Good Return on Equity ({roe:.1f}%) track record",
                    "rule_id": "good_roe",
                }
            )

    if roce is not None and roce > 20.0:
        pros.append(
            {
                "text": f"High Return on Capital Employed ({roce:.1f}%)",
                "rule_id": "high_roce",
            }
        )

    if div_yield is not None and div_yield > 2.0:
        pros.append(
            {
                "text": f"Healthy dividend yield of {div_yield:.1f}%",
                "rule_id": "good_dividend",
            }
        )

    if rev_growth is not None and rev_growth > 15.0:
        pros.append(
            {
                "text": f"Strong revenue growth rate of {rev_growth:.1f}%",
                "rule_id": "high_growth",
            }
        )

    if promoter_holding is not None and promoter_holding > 60.0:
        pros.append(
            {
                "text": f"High promoter holding at {promoter_holding:.1f}%",
                "rule_id": "high_promoter",
            }
        )

    # CONS
    if pe is not None and pe > 30.0:
        cons.append(
            {
                "text": f"Trading at an elevated P/E multiple of {pe:.1f}x",
                "rule_id": "high_pe",
            }
        )

    if pb is not None and pb > 6.0:
        cons.append(
            {
                "text": f"High Price-to-Book value ratio of {pb:.1f}x",
                "rule_id": "high_pb",
            }
        )

    if debt_equity is not None and debt_equity > 1.2:
        cons.append(
            {
                "text": f"Elevated debt-to-equity ratio of {debt_equity:.2f}",
                "rule_id": "high_debt",
            }
        )

    if interest_coverage is not None and interest_coverage < 2.0:
        cons.append(
            {
                "text": f"Low interest coverage ratio of {interest_coverage:.1f}x",
                "rule_id": "low_coverage",
            }
        )

    if pledged_pct is not None and pledged_pct > 5.0:
        cons.append(
            {
                "text": f"Promoter pledged shares stand at {pledged_pct:.1f}%",
                "rule_id": "pledged_risk",
            }
        )

    if promoter_holding is not None and promoter_holding < 30.0 and promoter_holding > 0:
        cons.append(
            {
                "text": f"Low promoter holding of {promoter_holding:.1f}%",
                "rule_id": "low_promoter",
            }
        )

    if div_yield is not None and div_yield == 0.0:
        cons.append(
            {
                "text": "Company does not currently pay a dividend",
                "rule_id": "no_dividend",
            }
        )

    return pros, cons
