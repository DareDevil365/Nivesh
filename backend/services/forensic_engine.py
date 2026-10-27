"""Financial screening models with explicit inputs, applicability and unavailable states."""

from services.data_fetcher import financial_value


def unavailable(model, reason, missing=None):
    return {
        "score": None,
        "status": "unavailable",
        "zone": "Unavailable",
        "flagged": None,
        "model": model,
        "description": reason,
        "missing_inputs": missing or [],
    }


def compute_forensic_metrics(profile, financials=None):
    fin = financials or {}

    def val(section, metric, i=-1):
        return financial_value(fin, section, metric, i)

    def bs(metric, i=-1):
        return val("balance_sheet", metric, i)

    def inc(metric, i=-1):
        return val("income_statement", metric, i)

    def cf(metric, i=-1):
        return val("cash_flow", metric, i)

    is_financial = any(
        w in (profile.get("sector", "") + " " + profile.get("industry", "")).lower()
        for w in ("financial", "bank", "insurance", "asset management")
    ) or profile.get("instrument_type") in {"ETF", "MUTUALFUND"}
    model = "Altman Z'' (non-financial, four-factor screening model)"
    z = unavailable(model, "Required statement inputs are unavailable.")
    inputs = {
        "Current Assets": bs("Current Assets"),
        "Current Liabilities": bs("Current Liabilities"),
        "Total Assets": bs("Total Assets"),
        "Retained Earnings": bs("Retained Earnings"),
        "Operating Income": inc("Operating Income"),
        "Total Equity": bs("Total Equity"),
        "Total Liabilities": bs("Total Liabilities"),
    }
    missing = [key for key, value in inputs.items() if value is None]
    if not missing and inputs["Total Assets"] > 0 and inputs["Total Liabilities"] > 0:
        ta = inputs["Total Assets"]
        factors = {
            "working_capital_assets": (inputs["Current Assets"] - inputs["Current Liabilities"])
            / ta,
            "retained_earnings_assets": inputs["Retained Earnings"] / ta,
            "ebit_assets": inputs["Operating Income"] / ta,
            "book_equity_liabilities": inputs["Total Equity"] / inputs["Total Liabilities"],
        }
        score = (
            6.56 * factors["working_capital_assets"]
            + 3.26 * factors["retained_earnings_assets"]
            + 6.72 * factors["ebit_assets"]
            + 1.05 * factors["book_equity_liabilities"]
        )
        z = {
            "score": round(score, 3),
            "zone": "Above upper threshold"
            if score > 2.6
            else "Below lower threshold"
            if score < 1.1
            else "Between thresholds",
            "status": "positive" if score > 2.6 else "negative" if score < 1.1 else "neutral",
            "model": model,
            "inputs": factors,
            "description": "Statistical distress screen, not a bankruptcy probability. Thresholds are not calibrated to Indian firms.",
            "missing_inputs": [],
        }
    else:
        z["missing_inputs"] = missing
    m = unavailable(
        "Beneish eight-variable M-score (cash-flow accrual variant)",
        "Two matching annual periods and all eight inputs are required.",
    )
    from datetime import date

    periods = fin.get("period_dates", [])
    consecutive = (
        len(periods) >= 2
        and 300 <= (date.fromisoformat(periods[-1]) - date.fromisoformat(periods[-2])).days <= 430
    )
    components = {}
    try:
        if not consecutive:
            raise ValueError("Two consecutive annual periods are required.")

        def ratio(a, b):
            if a is None or b is None or b <= 0:
                raise ValueError("Missing input or non-positive denominator")
            return a / b

        rev, oldrev = inc("Total Revenue"), inc("Total Revenue", -2)
        ta, oldta = bs("Total Assets"), bs("Total Assets", -2)

        def sub(a, b):
            if a is None or b is None:
                raise ValueError("Missing component")
            return a - b

        gross = (
            inc("Gross Profit")
            if inc("Gross Profit") is not None
            else sub(rev, inc("Cost Of Revenue"))
        )
        oldgross = (
            inc("Gross Profit", -2)
            if inc("Gross Profit", -2) is not None
            else sub(oldrev, inc("Cost Of Revenue", -2))
        )
        dep = inc("Depreciation") if inc("Depreciation") is not None else cf("Depreciation")
        olddep = (
            inc("Depreciation", -2)
            if inc("Depreciation", -2) is not None
            else cf("Depreciation", -2)
        )
        components = {
            "DSRI": ratio(ratio(bs("Receivables"), rev), ratio(bs("Receivables", -2), oldrev)),
            "GMI": ratio(ratio(oldgross, oldrev), ratio(gross, rev)),
            "AQI": ratio(
                1 - ratio(bs("Current Assets") + bs("Fixed Assets / PPE"), ta),
                1 - ratio(bs("Current Assets", -2) + bs("Fixed Assets / PPE", -2), oldta),
            ),
            "SGI": ratio(rev, oldrev),
            "DEPI": ratio(
                ratio(olddep, olddep + bs("Fixed Assets / PPE", -2)),
                ratio(dep, dep + bs("Fixed Assets / PPE")),
            ),
            "SGAI": ratio(ratio(inc("SG&A"), rev), ratio(inc("SG&A", -2), oldrev)),
            "LVGI": ratio(
                ratio(bs("Current Liabilities") + bs("Long Term Debt"), ta),
                ratio(bs("Current Liabilities", -2) + bs("Long Term Debt", -2), oldta),
            ),
            "TATA": ratio(sub(inc("Net Income"), cf("Operating Cash Flow")), ta),
        }
        score = (
            -4.84
            + 0.920 * components["DSRI"]
            + 0.528 * components["GMI"]
            + 0.404 * components["AQI"]
            + 0.892 * components["SGI"]
            + 0.115 * components["DEPI"]
            - 0.172 * components["SGAI"]
            + 4.679 * components["TATA"]
            - 0.327 * components["LVGI"]
        )
        m = {
            "score": round(score, 3),
            "flagged": score > -1.78,
            "status": "negative" if score > -1.78 else "neutral",
            "model": "Beneish eight-variable M-score (cash-flow accrual variant)",
            "inputs": components,
            "description": "Above -1.78 is a screening flag, not evidence of fraud. TATA uses net income minus operating cash flow divided by assets. Verify the underlying filings.",
            "missing_inputs": [],
        }
    except (ValueError, TypeError, ZeroDivisionError):
        m["missing_inputs"] = [
            "Two annual values for revenue, receivables, gross profit/COGS, assets, current assets, PPE, depreciation, SG&A and debt; latest net income and operating cash flow. Non-positive ratio denominators are unsupported."
        ]
    ccc = {
        "ccc_days": None,
        "dio_days": None,
        "dso_days": None,
        "dpo_days": None,
        "is_estimated": False,
        "description": "Matching periods and average working-capital balances are required.",
    }
    try:
        if not consecutive:
            raise ValueError("Consecutive annual periods required.")

        def average(metric):
            a, b = bs(metric), bs(metric, -2)
            if a is None or b is None:
                raise ValueError()
            return (a + b) / 2

        revenue, cogs = inc("Total Revenue"), inc("Cost Of Revenue")
        if not revenue or not cogs or revenue <= 0 or cogs <= 0:
            raise ValueError()
        dio, dso, dpo = (
            365 * average("Inventory") / cogs,
            365 * average("Receivables") / revenue,
            365 * average("Payables") / cogs,
        )
        ccc.update(
            ccc_days=round(dio + dso - dpo, 1),
            dio_days=round(dio, 1),
            dso_days=round(dso, 1),
            dpo_days=round(dpo, 1),
            description="Uses two-year average balances and annual revenue/COGS; 365-day convention.",
        )
    except (ValueError, TypeError):
        pass
    if is_financial:
        z = unavailable(model, "This model is not applicable to financial institutions or funds.")
        m = unavailable(m["model"], "This model is not applied to financial institutions or funds.")
        ccc = {
            **ccc,
            "ccc_days": None,
            "dio_days": None,
            "dso_days": None,
            "dpo_days": None,
            "description": "Not applicable to financial institutions or funds.",
        }
    pledge = profile.get("pledged_shares_pct")
    return {
        "ticker": profile.get("ticker"),
        "altman_z": z,
        "beneish_m": m,
        "cash_conversion_cycle": ccc,
        "promoter_pledge": {
            "pledged_pct": pledge,
            "status": "unavailable" if pledge is None else "negative" if pledge > 5 else "neutral",
            "label": "Pledge data unavailable" if pledge is None else "Reported pledge",
            "description": "Verify promoter pledge in exchange shareholding disclosures.",
        },
        "period": fin.get("period_dates", [None])[-1] if fin.get("period_dates") else None,
        "source": "Calculated from Yahoo Finance annual statements; values may be restated.",
    }
