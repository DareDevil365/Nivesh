import time
import logging
from typing import Dict, Any, Optional, List
import yfinance as yf
import pandas as pd
import numpy as np
from services.cache_manager import cache_manager
from services.nse_stock_master import resolve_symbol_alias, NSE_MASTER_LIST

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def normalize_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    ticker = resolve_symbol_alias(ticker)
    if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
        ticker = f"{ticker}.NS"
    return resolve_symbol_alias(ticker)

def _cr(val) -> Optional[float]:
    """Convert raw rupees to ₹ Crores, safely."""
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return round(float(val) / 10_000_000.0, 2)
    except Exception:
        return None

def _safe_float(val, digits: int = 2) -> Optional[float]:
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return round(float(val), digits)
    except Exception:
        return None

def _row(df: pd.DataFrame, *candidates) -> Optional[pd.Series]:
    """Return first matching row from dataframe index, trying multiple candidate names."""
    if df is None or df.empty:
        return None
    for name in candidates:
        if name in df.index:
            return df.loc[name]
    return None

def _series_to_cr_list(series: Optional[pd.Series], max_cols: int = 10) -> List[Optional[float]]:
    if series is None:
        return []
    return [_cr(v) for v in series.iloc[:max_cols]]

def _series_to_float_list(series: Optional[pd.Series], max_cols: int = 10, digits: int = 2) -> List[Optional[float]]:
    if series is None:
        return []
    return [_safe_float(v, digits) for v in series.iloc[:max_cols]]


# ─────────────────────────────────────────────
# COMPANY PROFILE
# ─────────────────────────────────────────────

def get_company_profile(ticker: str) -> Dict[str, Any]:
    resolved_ticker = normalize_ticker(ticker)
    cache_key = f"company_profile_v2:{resolved_ticker}"

    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    master_meta = NSE_MASTER_LIST.get(resolved_ticker, {})
    name = master_meta.get("name", resolved_ticker.replace(".NS", "").replace(".BO", ""))
    sector = master_meta.get("sector", "NSE Equity")
    industry = master_meta.get("industry", "General Equity")

    try:
        yf_ticker = yf.Ticker(resolved_ticker)
        info = yf_ticker.info or {}

        if not info or (not info.get("shortName") and not info.get("longName") and not info.get("regularMarketPrice") and not info.get("currentPrice")):
            alt_ticker = resolved_ticker.replace(".NS", "")
            alt_info = yf.Ticker(alt_ticker).info or {}
            if alt_info and (alt_info.get("shortName") or alt_info.get("longName") or alt_info.get("regularMarketPrice")):
                info = alt_info

        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or info.get("open")

        if not price and not info.get("shortName") and not info.get("longName"):
            raise ValueError(f"Real-time market data unavailable on exchange for symbol {ticker}")

        name = info.get("longName") or info.get("shortName") or name
        sector = info.get("sector") or sector
        industry = info.get("industry") or industry
        isin = info.get("isin") or None

        current_price = float(price) if price else 0.0
        prev_close = info.get("previousClose") or price

        day_change = 0.0
        day_change_pct = 0.0
        if price and prev_close:
            day_change = round(float(price) - float(prev_close), 2)
            day_change_pct = round((day_change / float(prev_close)) * 100, 2)

        mcap = info.get("marketCap")
        market_cap = float(mcap) if mcap else 0.0
        market_cap_cr = round(market_cap / 10_000_000.0, 2) if mcap else 0.0

        pe = _safe_float(info.get("trailingPE"))
        pb = _safe_float(info.get("priceToBook"))
        eps = _safe_float(info.get("trailingEps"))
        book_value = _safe_float(info.get("bookValue"))
        face_value = _safe_float(info.get("faceValue") or 10.0)  # yfinance rarely provides this, default ₹10

        week_high = _safe_float(info.get("fiftyTwoWeekHigh"))
        week_low = _safe_float(info.get("fiftyTwoWeekLow"))

        roe_raw = info.get("returnOnEquity")
        roe = None
        if roe_raw is not None:
            try:
                roe = round(float(roe_raw) * 100 if abs(float(roe_raw)) < 1.0 else float(roe_raw), 2)
            except Exception:
                roe = None

        # ROCE calculation
        roce = None
        try:
            financials = yf_ticker.financials
            balance_sheet = yf_ticker.balance_sheet
            if financials is not None and not financials.empty and balance_sheet is not None and not balance_sheet.empty:
                ebit = _row(financials, "EBIT", "Operating Income")
                total_assets = _row(balance_sheet, "Total Assets")
                curr_liab = _row(balance_sheet, "Current Liabilities", "Total Current Liabilities Net Minority Interest")
                if ebit is not None and total_assets is not None:
                    ebit_val = float(ebit.iloc[0])
                    ta_val = float(total_assets.iloc[0])
                    cl_val = float(curr_liab.iloc[0]) if curr_liab is not None else 0
                    capital_employed = ta_val - cl_val
                    if capital_employed > 0:
                        roce = round((ebit_val / capital_employed) * 100, 2)
        except Exception:
            roce = None

        if roce is None and roe is not None:
            roce = roe

        de_raw = info.get("debtToEquity")
        debt_equity = None
        if de_raw is not None:
            try:
                de = float(de_raw)
                debt_equity = round(de / 100.0 if de > 5.0 else de, 2)
            except Exception:
                pass

        dy_raw = info.get("dividendYield")
        div_yield = 0.0
        if dy_raw is not None:
            try:
                dy = float(dy_raw)
                # yfinance inconsistency: sometimes returns 0.005 (decimal), sometimes 0.5 (percentage)
                # Values < 0.15 are almost certainly decimal fractions → multiply by 100
                # Values >= 0.15 are already in percentage form (e.g. 1.5 = 1.5%)
                if dy < 0.15:
                    div_yield = round(dy * 100, 2)
                else:
                    div_yield = round(dy, 2)
                # Sanity clamp: div yield > 25% is almost certainly a data error
                if div_yield > 25.0:
                    div_yield = 0.0
            except Exception:
                pass

        insider_pct = info.get("heldPercentInsiders")
        promoter_holding = round(float(insider_pct) * 100, 2) if insider_pct is not None else None

        current_ratio = _safe_float(info.get("currentRatio"))

        # Interest coverage: EBIT / Interest Expense
        interest_coverage = None
        try:
            financials = yf_ticker.financials
            if financials is not None and not financials.empty:
                ebit_s = _row(financials, "EBIT", "Operating Income")
                int_s = _row(financials, "Interest Expense", "Net Interest Income")
                if ebit_s is not None and int_s is not None:
                    ebit_v = float(ebit_s.iloc[0])
                    int_v = abs(float(int_s.iloc[0]))
                    if int_v > 0:
                        interest_coverage = round(ebit_v / int_v, 2)
        except Exception:
            pass

        payout_ratio = _safe_float(info.get("payoutRatio"), 1)
        if payout_ratio and payout_ratio < 1.0:
            payout_ratio = round(payout_ratio * 100, 1)

        long_summary = info.get("longBusinessSummary") or ""

        profile_data = {
            "ticker": resolved_ticker,
            "original_ticker": ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "isin": isin,
            "website": info.get("website") or "",
            "about": long_summary[:1200] if long_summary else "",
            "current_price": current_price,
            "day_change": day_change,
            "day_change_pct": day_change_pct,
            "week_high_52": week_high,
            "week_low_52": week_low,
            "market_cap": market_cap,
            "market_cap_cr": market_cap_cr,
            "pe": pe,
            "pb": pb,
            "eps": eps,
            "book_value": book_value,
            "face_value": face_value if face_value else 10.0,
            "roe": roe,
            "roce": roce,
            "debt_equity": debt_equity,
            "div_yield": div_yield,
            "revenue_growth_3yr": _safe_float(info.get("revenueGrowth"), 2) and round(float(info.get("revenueGrowth", 0)) * 100, 2) if info.get("revenueGrowth") else None,
            "eps_growth_3yr": round(float(info.get("earningsGrowth", 0)) * 100, 2) if info.get("earningsGrowth") else None,
            "promoter_holding": promoter_holding,
            "pledged_shares_pct": 0.0,
            "current_ratio": current_ratio,
            "interest_coverage": interest_coverage,
            "payout_ratio": payout_ratio,
            "operating_cf_debt_ratio": None,
            "data_source": "live",
            "delayed_badge": True
        }

        cache_manager.set(cache_key, profile_data, ttl=900)
        return profile_data

    except Exception as e:
        logger.warning(f"Live data fetch failed for {ticker} ({resolved_ticker}): {e}")
        raise ValueError(f"Real-time market data unavailable for ticker '{ticker}'. Error: {str(e)}")


# ─────────────────────────────────────────────
# CHART DATA
# ─────────────────────────────────────────────

def get_chart_data(ticker: str, period: str = "1y", interval: str = "1d") -> Dict[str, Any]:
    resolved_ticker = normalize_ticker(ticker)
    cache_key = f"chart:{resolved_ticker}:{period}:{interval}"

    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    try:
        yf_ticker = yf.Ticker(resolved_ticker)
        df = yf_ticker.history(period=period, interval=interval)

        if df.empty:
            alt_ticker = resolved_ticker.replace(".NS", "")
            df = yf.Ticker(alt_ticker).history(period=period, interval=interval)

        if df.empty:
            return {"ticker": resolved_ticker, "period": period, "interval": interval, "bars": [], "error": f"No price history for {ticker}", "data_source": "unavailable"}

        bars = []
        for index, row in df.iterrows():
            try:
                o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
                if np.isnan(o) or np.isnan(h) or np.isnan(l) or np.isnan(c) or o <= 0 or h <= 0 or l <= 0 or c <= 0:
                    continue
                date_str = index.strftime("%Y-%m-%d")
                vol = int(row["Volume"]) if not np.isnan(row["Volume"]) else 0
                bars.append({
                    "time": date_str,
                    "open": round(o, 2),
                    "high": round(h, 2),
                    "low": round(l, 2),
                    "close": round(c, 2),
                    "volume": vol
                })
            except Exception:
                continue

        chart_result = {"ticker": resolved_ticker, "period": period, "interval": interval, "bars": bars, "data_source": "live"}
        ttl = 3600 if interval == "1d" else 300
        cache_manager.set(cache_key, chart_result, ttl=ttl)
        return chart_result

    except Exception as e:
        logger.warning(f"Failed to fetch live chart for {ticker}: {e}")
        return {"ticker": resolved_ticker, "period": period, "interval": interval, "bars": [], "error": f"Failed to fetch price data for {ticker}", "data_source": "unavailable"}


# ─────────────────────────────────────────────
# ANNUAL FINANCIAL STATEMENTS (enhanced)
# ─────────────────────────────────────────────

def get_company_financials(ticker: str) -> Dict[str, Any]:
    resolved_ticker = normalize_ticker(ticker)
    cache_key = f"financials_v2:{resolved_ticker}"

    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    try:
        yf_ticker = yf.Ticker(resolved_ticker)
        fin = yf_ticker.financials        # Annual P&L — columns are dates newest first
        bs = yf_ticker.balance_sheet      # Annual Balance Sheet
        cf = yf_ticker.cashflow           # Annual Cash Flow

        years = []
        income_rows = []
        bs_rows = []
        cf_rows = []

        if fin is not None and not fin.empty:
            cols = list(fin.columns[:10])
            years = [f"FY{c.strftime('%y')}" for c in reversed(cols)]

            # Income Statement — extract all meaningful rows
            income_map = [
                ("Total Revenue", "Total Revenue", "Revenue"),
                ("Operating Revenue", "Operating Revenue"),
                ("Cost Of Revenue", "Cost Of Revenue", "Cost of Goods Sold"),
                ("Gross Profit", "Gross Profit"),
                ("Operating Income", "Operating Income", "EBIT"),
                ("EBITDA", "EBITDA", "Normalized EBITDA"),
                ("Net Income", "Net Income", "Net Income Common Stockholders"),
                ("Interest Expense", "Interest Expense", "Net Interest Income"),
                ("Pretax Income", "Pretax Income"),
                ("Tax Provision", "Tax Provision"),
                ("Diluted EPS", "Diluted EPS", "Basic EPS"),
            ]
            for label, *keys in income_map:
                s = _row(fin, *keys)
                if s is not None:
                    vals = _series_to_cr_list(s.iloc[::-1], max_cols=10)
                    if any(v is not None for v in vals):
                        income_rows.append({"metric": label, "values": vals, "unit": "₹ Cr"})

        if bs is not None and not bs.empty:
            bs_map = [
                ("Equity Capital", "Common Stock", "Capital Stock"),
                ("Reserves & Surplus", "Retained Earnings", "Stockholders Equity"),
                ("Total Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"),
                ("Total Debt", "Total Debt", "Long Term Debt"),
                ("Short Term Borrowings", "Current Debt", "Short Term Debt"),
                ("Long Term Borrowings", "Long Term Debt"),
                ("Total Liabilities", "Total Liabilities Net Minority Interest", "Total Liabilities"),
                ("Fixed Assets / PPE", "Net PPE", "Gross PPE"),
                ("Investments", "Investments And Advances", "Long Term Investments"),
                ("Current Assets", "Current Assets", "Total Current Assets"),
                ("Current Liabilities", "Current Liabilities", "Total Current Liabilities Net Minority Interest"),
                ("Total Assets", "Total Assets"),
                ("Cash & Equivalents", "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"),
            ]
            for label, *keys in bs_map:
                s = _row(bs, *keys)
                if s is not None:
                    vals = _series_to_cr_list(s.iloc[::-1], max_cols=10)
                    if any(v is not None for v in vals):
                        bs_rows.append({"metric": label, "values": vals, "unit": "₹ Cr"})

        if cf is not None and not cf.empty:
            cf_map = [
                ("Operating Cash Flow", "Operating Cash Flow", "Cash From Operations"),
                ("Capital Expenditure", "Capital Expenditure", "Purchase Of PPE"),
                ("Free Cash Flow", "Free Cash Flow"),
                ("Investing Cash Flow", "Investing Cash Flow"),
                ("Financing Cash Flow", "Financing Cash Flow"),
                ("Dividends Paid", "Common Stock Dividend Paid", "Payment Of Dividends"),
                ("Debt Repayment", "Repayment Of Debt", "Long Term Debt Issuance"),
            ]
            for label, *keys in cf_map:
                s = _row(cf, *keys)
                if s is not None:
                    vals = _series_to_cr_list(s.iloc[::-1], max_cols=10)
                    if any(v is not None for v in vals):
                        cf_rows.append({"metric": label, "values": vals, "unit": "₹ Cr"})

        if not income_rows and not bs_rows:
            res = {"ticker": resolved_ticker, "years": [], "income_statement": [], "balance_sheet": [], "cash_flow": [], "data_source": "unavailable", "message": "Historical financial statements unavailable from exchange provider."}
            return res

        res = {"ticker": resolved_ticker, "years": years, "income_statement": income_rows, "balance_sheet": bs_rows, "cash_flow": cf_rows, "data_source": "live"}
        cache_manager.set(cache_key, res, ttl=3600)
        return res

    except Exception as e:
        logger.warning(f"Financials fetch failed for {ticker}: {e}")
        return {"ticker": resolved_ticker, "years": [], "income_statement": [], "balance_sheet": [], "cash_flow": [], "data_source": "unavailable", "message": "Historical financial statements unavailable."}


# ─────────────────────────────────────────────
# QUARTERLY RESULTS (NEW)
# ─────────────────────────────────────────────

def get_quarterly_results(ticker: str) -> Dict[str, Any]:
    """
    Extracts 8-12 quarters of P&L data from yfinance quarterly_financials.
    Returns Screener.in-style quarterly results table.
    """
    resolved_ticker = normalize_ticker(ticker)
    cache_key = f"quarterly_results_v3:{resolved_ticker}"

    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    try:
        yf_ticker = yf.Ticker(resolved_ticker)
        qfin = yf_ticker.quarterly_financials   # Quarterly P&L
        qbs = yf_ticker.quarterly_balance_sheet

        if qfin is None or qfin.empty:
            return {"ticker": resolved_ticker, "quarters": [], "rows": [], "data_source": "unavailable", "message": "Quarterly results unavailable from exchange."}

        # Columns = quarter end dates, newest first
        cols = list(qfin.columns[:12])
        quarters = [c.strftime("%b %Y") for c in reversed(cols)]

        rows = []

        def q_row(label: str, *keys, unit="₹ Cr", pct=False, raw=False):
            s = _row(qfin, *keys)
            if s is not None:
                rev_vals = list(s.iloc[::-1].iloc[:12])
                if pct:
                    vals = [_safe_float(v, 1) for v in rev_vals]
                elif raw:
                    vals = [_safe_float(v, 2) for v in rev_vals]
                else:
                    vals = [_cr(v) for v in rev_vals]
                if any(v is not None for v in vals):
                    rows.append({"metric": label, "values": vals, "unit": "%" if pct else unit, "highlight": label in ("Operating Profit", "Net Profit", "EBITDA")})

        # Core P&L rows
        q_row("Sales", "Total Revenue", "Revenue")
        q_row("Expenses", "Total Expenses", "Cost Of Revenue", "Operating Expense")
        q_row("Operating Profit", "Operating Income", "EBIT")

        # Compute OPM% from above if we can
        rev_s = _row(qfin, "Total Revenue", "Revenue")
        op_s = _row(qfin, "Operating Income", "EBIT")
        if rev_s is not None and op_s is not None:
            opm_vals = []
            for rv, op in zip(list(rev_s.iloc[::-1].iloc[:12]), list(op_s.iloc[::-1].iloc[:12])):
                try:
                    opm_vals.append(round((float(op) / float(rv)) * 100, 1) if rv and float(rv) != 0 else None)
                except Exception:
                    opm_vals.append(None)
            if any(v is not None for v in opm_vals):
                rows.append({"metric": "OPM %", "values": opm_vals, "unit": "%", "highlight": False})

        q_row("Other Income", "Other Income Expense", "Non Operating Income")
        q_row("Interest", "Interest Expense")
        q_row("Depreciation", "Depreciation And Amortization In Income Statement", "Reconciled Depreciation", "Depreciation Amortization Depletion")
        q_row("Profit Before Tax", "Pretax Income")

        # Tax %
        pbt_s = _row(qfin, "Pretax Income")
        tax_s = _row(qfin, "Tax Provision", "Income Tax Expense")
        if pbt_s is not None and tax_s is not None:
            tax_pct_vals = []
            for pbt, tx in zip(list(pbt_s.iloc[::-1].iloc[:12]), list(tax_s.iloc[::-1].iloc[:12])):
                try:
                    tax_pct_vals.append(round((float(tx) / float(pbt)) * 100, 1) if pbt and float(pbt) != 0 else None)
                except Exception:
                    tax_pct_vals.append(None)
            if any(v is not None for v in tax_pct_vals):
                rows.append({"metric": "Tax %", "values": tax_pct_vals, "unit": "%", "highlight": False})

        q_row("Net Profit", "Net Income", "Net Income Common Stockholders")
        q_row("EPS (₹)", "Diluted EPS", "Basic EPS", unit="₹", raw=True)

        if not rows:
            return {"ticker": resolved_ticker, "quarters": [], "rows": [], "data_source": "unavailable", "message": "Quarterly financial data unavailable."}

        res = {"ticker": resolved_ticker, "quarters": quarters, "rows": rows, "data_source": "live"}
        cache_manager.set(cache_key, res, ttl=3600)
        return res

    except Exception as e:
        logger.warning(f"Quarterly results fetch failed for {ticker}: {e}")
        return {"ticker": resolved_ticker, "quarters": [], "rows": [], "data_source": "unavailable", "message": f"Quarterly results unavailable: {str(e)}"}


# ─────────────────────────────────────────────
# HISTORICAL KEY RATIOS (NEW)
# ─────────────────────────────────────────────

def get_historical_ratios(ticker: str) -> Dict[str, Any]:
    """
    Computes historical key financial ratios across multiple years.
    Returns Screener.in-style ratios table with 5-10 year data.
    """
    resolved_ticker = normalize_ticker(ticker)
    cache_key = f"historical_ratios_v2:{resolved_ticker}"

    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    try:
        yf_ticker = yf.Ticker(resolved_ticker)
        fin = yf_ticker.financials
        bs = yf_ticker.balance_sheet
        cf = yf_ticker.cashflow

        if (fin is None or fin.empty) and (bs is None or bs.empty):
            return {"ticker": resolved_ticker, "years": [], "rows": [], "data_source": "unavailable", "message": "Historical ratio data unavailable."}

        cols = list(fin.columns[:10]) if fin is not None and not fin.empty else []
        years = [f"FY{c.strftime('%y')}" for c in reversed(cols)]

        rows = []

        # Helper: compute ratio series across all years
        def add_ratio(label, values_list, unit="%", digits=2):
            clean = [_safe_float(v, digits) for v in values_list]
            if any(v is not None for v in clean):
                rows.append({"metric": label, "values": clean, "unit": unit})

        n = len(cols)

        # ─── Profitability ───
        rev = _row(fin, "Total Revenue", "Revenue")
        op = _row(fin, "Operating Income", "EBIT")
        net = _row(fin, "Net Income", "Net Income Common Stockholders")
        ebitda = _row(fin, "EBITDA", "Normalized EBITDA")

        if rev is not None and op is not None:
            opm = [round((float(op.iloc[i]) / float(rev.iloc[i])) * 100, 1) if rev.iloc[i] and float(rev.iloc[i]) != 0 else None for i in range(n)]
            add_ratio("OPM %", reversed(opm))

        if rev is not None and net is not None:
            npm = [round((float(net.iloc[i]) / float(rev.iloc[i])) * 100, 1) if rev.iloc[i] and float(rev.iloc[i]) != 0 else None for i in range(n)]
            add_ratio("NPM %", reversed(npm))

        # ─── Returns ───
        if bs is not None and not bs.empty:
            equity = _row(bs, "Stockholders Equity", "Total Equity Gross Minority Interest")
            total_assets_s = _row(bs, "Total Assets")
            curr_liab_s = _row(bs, "Current Liabilities", "Total Current Liabilities Net Minority Interest")

            if net is not None and equity is not None:
                roe_vals = []
                for i in range(min(n, len(equity))):
                    try:
                        eq = float(equity.iloc[i])
                        ni = float(net.iloc[i])
                        roe_vals.append(round((ni / eq) * 100, 1) if eq != 0 else None)
                    except Exception:
                        roe_vals.append(None)
                add_ratio("ROE %", reversed(roe_vals))

            if op is not None and total_assets_s is not None:
                roce_vals = []
                for i in range(min(n, len(total_assets_s))):
                    try:
                        ta = float(total_assets_s.iloc[i])
                        cl = float(curr_liab_s.iloc[i]) if curr_liab_s is not None else 0
                        ce = ta - cl
                        oi = float(op.iloc[i])
                        roce_vals.append(round((oi / ce) * 100, 1) if ce != 0 else None)
                    except Exception:
                        roce_vals.append(None)
                add_ratio("ROCE %", reversed(roce_vals))

            # Return on Assets
            if net is not None and total_assets_s is not None:
                roa_vals = []
                for i in range(min(n, len(total_assets_s))):
                    try:
                        ta = float(total_assets_s.iloc[i])
                        ni = float(net.iloc[i])
                        roa_vals.append(round((ni / ta) * 100, 1) if ta != 0 else None)
                    except Exception:
                        roa_vals.append(None)
                add_ratio("Return on Assets %", reversed(roa_vals))

            # Debt / Equity
            debt_s = _row(bs, "Total Debt", "Long Term Debt")
            if debt_s is not None and equity is not None:
                de_vals = []
                for i in range(min(n, len(equity))):
                    try:
                        eq = float(equity.iloc[i])
                        dt = float(debt_s.iloc[i])
                        de_vals.append(round(dt / eq, 2) if eq != 0 else None)
                    except Exception:
                        de_vals.append(None)
                add_ratio("Debt / Equity", reversed(de_vals), unit="x")

        # ─── Cash Flow ───
        if cf is not None and not cf.empty and rev is not None:
            ocf = _row(cf, "Operating Cash Flow", "Cash From Operations")
            if ocf is not None:
                ocf_margin = []
                for i in range(min(n, len(ocf))):
                    try:
                        rv = float(rev.iloc[i])
                        oc = float(ocf.iloc[i])
                        ocf_margin.append(round((oc / rv) * 100, 1) if rv != 0 else None)
                    except Exception:
                        ocf_margin.append(None)
                add_ratio("Operating CF Margin %", reversed(ocf_margin))

        # ─── Valuation (single year snapshot — historical P/E is hard without price series) ───
        # Add whatever is available from info dict as single point for reference
        info = {}
        try:
            info = yf_ticker.info or {}
        except Exception:
            pass

        pe_val = _safe_float(info.get("trailingPE"))
        pb_val = _safe_float(info.get("priceToBook"))
        div_payout = _safe_float(info.get("payoutRatio"))
        if div_payout and div_payout < 1.0:
            div_payout = round(div_payout * 100, 1)

        # Compute CAGR rows
        def cagr(values_list):
            vals = [v for v in values_list if v is not None]
            if len(vals) >= 2:
                try:
                    start, end = vals[0], vals[-1]
                    n_periods = len(vals) - 1
                    if start and start > 0 and end and n_periods > 0:
                        return round(((end / start) ** (1 / n_periods) - 1) * 100, 1)
                except Exception:
                    pass
            return None

        # Revenue growth CAGR
        if rev is not None:
            rev_vals_cr = [_cr(v) for v in reversed(list(rev.iloc[:n]))]
            cagr_rev = cagr(rev_vals_cr)
            if cagr_rev:
                add_ratio(f"Revenue CAGR ({len(years)}yr)", [cagr_rev] + [None] * (len(years) - 1), unit="%")

        if net is not None:
            net_vals_cr = [_cr(v) for v in reversed(list(net.iloc[:n]))]
            cagr_net = cagr(net_vals_cr)
            if cagr_net:
                add_ratio(f"Net Profit CAGR ({len(years)}yr)", [cagr_net] + [None] * (len(years) - 1), unit="%")

        if not rows:
            return {"ticker": resolved_ticker, "years": years, "rows": [], "data_source": "unavailable", "message": "Unable to compute historical ratios."}

        res = {"ticker": resolved_ticker, "years": years, "rows": rows, "data_source": "live", "current_pe": pe_val, "current_pb": pb_val, "current_div_payout": div_payout}
        cache_manager.set(cache_key, res, ttl=3600)
        return res

    except Exception as e:
        logger.warning(f"Historical ratios fetch failed for {ticker}: {e}")
        return {"ticker": resolved_ticker, "years": [], "rows": [], "data_source": "unavailable", "message": f"Historical ratio data unavailable: {str(e)}"}


# ─────────────────────────────────────────────
# SHAREHOLDING PATTERN (enhanced)
# ─────────────────────────────────────────────

def get_company_shareholding(ticker: str) -> Dict[str, Any]:
    """
    Extracts shareholding pattern with best-effort multi-category breakdown.
    yfinance provides limited Indian shareholding data; this maximizes what's available.
    """
    resolved_ticker = normalize_ticker(ticker)
    cache_key = f"shareholding_v2:{resolved_ticker}"

    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    try:
        yf_ticker = yf.Ticker(resolved_ticker)
        info = yf_ticker.info or {}

        insider_pct = info.get("heldPercentInsiders")
        inst_pct = info.get("heldPercentInstitutions")

        promoter = round(float(insider_pct) * 100, 2) if insider_pct is not None else None
        institutions = round(float(inst_pct) * 100, 2) if inst_pct is not None else None

        # Try to get institutional holders for FII/DII split (best effort)
        fii = None
        dii = None
        try:
            inst_holders = yf_ticker.institutional_holders
            if inst_holders is not None and not inst_holders.empty and institutions is not None:
                # Rough heuristic: foreign institutions = FII, domestic = DII
                # yfinance doesn't separate FII/DII for Indian stocks
                # Use institutions total, split 50/50 as placeholder until NSE data
                fii = round(institutions * 0.5, 2)
                dii = round(institutions * 0.5, 2)
        except Exception:
            pass

        if promoter is None and institutions is None:
            return {
                "ticker": resolved_ticker,
                "quarters": [],
                "breakdown": [],
                "pledged_pct": None,
                "data_source": "unavailable",
                "message": "Shareholding pattern not available for this stock. Visit NSE India for official data."
            }

        # Build breakdown — using what we have
        breakdown = []
        total_accounted = 0.0

        if promoter is not None:
            breakdown.append({"category": "Promoter", "key": "Promoter", "pct": promoter, "trend": [promoter], "color": "#2ECC71"})
            total_accounted += promoter

        if fii is not None:
            breakdown.append({"category": "FII", "key": "FII", "pct": fii, "trend": [fii], "color": "#3B82F6"})
            total_accounted += fii

        if dii is not None:
            breakdown.append({"category": "DII", "key": "DII", "pct": dii, "trend": [dii], "color": "#9333EA"})
            total_accounted += dii

        public = round(max(0.0, 100.0 - total_accounted), 2)
        breakdown.append({"category": "Public & Others", "key": "Public & Others", "pct": public, "trend": [public], "color": "#8FA096"})

        res = {
            "ticker": resolved_ticker,
            "quarters": ["Latest"],
            "breakdown": breakdown,
            "pledged_pct": 0.0,
            "data_source": "live",
            "note": "FII/DII split is estimated. Promoter holding sourced from exchange insider data."
        }
        cache_manager.set(cache_key, res, ttl=3600)
        return res

    except Exception as e:
        logger.warning(f"Shareholding fetch failed for {ticker}: {e}")
        return {
            "ticker": resolved_ticker,
            "quarters": [],
            "breakdown": [],
            "pledged_pct": None,
            "data_source": "unavailable",
            "message": "Shareholding pattern data unavailable from exchange."
        }
