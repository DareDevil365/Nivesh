"""Yahoo Finance adapter. Missing values stay missing; periods and units are explicit."""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

import numpy as np
import pandas as pd
import yfinance as yf

from services.cache_manager import cache_manager
from services.nse_stock_master import NSE_MASTER_LIST, resolve_symbol_alias

logger = logging.getLogger(__name__)


class MarketDataUnavailable(ValueError):
    """Provider returned no usable quote; not an invalid user input."""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def normalize_ticker(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z0-9&^][A-Z0-9&.\-^]{0,29}", symbol):
        raise ValueError("Enter a valid NSE or BSE symbol.")
    symbol = resolve_symbol_alias(symbol)
    if symbol in {"^NSEI", "^BSESN"}:
        return symbol
    if not symbol.endswith((".NS", ".BO")):
        symbol += ".NS"
    return resolve_symbol_alias(symbol)


def _safe_float(value, digits=2):
    try:
        number = float(value)
        return round(number, digits) if np.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _cr(value):
    value = _safe_float(value, 8)
    return round(value / 10_000_000, 4) if value is not None else None


def _row(frame, *names):
    if frame is None or frame.empty:
        return None
    for name in names:
        if name in frame.index:
            return frame.loc[name]
    return None


def _at(frame, date, *names):
    row = _row(frame, *names)
    return _safe_float(row.get(date), 8) if row is not None else None


def _percent(value):
    value = _safe_float(value, 8)
    return round(value * 100, 2) if value is not None else None


def _cagr(frame, *names):
    row = _row(frame, *names)
    if row is None:
        return None
    dated = [(pd.Timestamp(d), _safe_float(v, 8)) for d, v in row.items()]
    dated = sorted((d, v) for d, v in dated if v is not None)
    if len(dated) < 4:
        return None
    end, latest = dated[-1]
    eligible = [(d, v) for d, v in dated[:-1] if 2.8 <= (end - d).days / 365.25 <= 3.2]
    if not eligible:
        return None
    start, first = eligible[-1]
    return (
        round(((latest / first) ** (365.25 / (end - start).days) - 1) * 100, 2)
        if first > 0 and latest > 0
        else None
    )


def get_company_profile(ticker: str) -> Dict[str, Any]:
    symbol = normalize_ticker(ticker)
    key = f"profile_v4:{symbol}"
    cached = cache_manager.get(key)
    if cached:
        return cached
    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}
        price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        if price is None or price <= 0:
            raise ValueError("No current quote was returned by the market data provider.")
        currency = info.get("currency")
        if currency and currency != "INR":
            raise ValueError("Provider returned a non-INR instrument. Verify the exchange symbol.")

        def statement(name):
            try:
                frame = getattr(stock, name)
                return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()
            except Exception:
                return pd.DataFrame()

        fin, bs, cf = (statement(name) for name in ("financials", "balance_sheet", "cashflow"))
        dates = (
            sorted(set(fin.columns) & set(bs.columns)) if fin is not None and bs is not None else []
        )
        date = dates[-1] if dates else None

        def value(frame, *names):
            return _at(frame, date, *names) if date is not None else None

        assets = value(bs, "Total Assets")
        liabilities = value(
            bs, "Current Liabilities", "Total Current Liabilities Net Minority Interest"
        )
        ebit = value(fin, "EBIT", "Operating Income")
        interest = value(fin, "Interest Expense")
        debt = value(bs, "Total Debt")
        ocf = value(cf, "Operating Cash Flow")
        fcf = value(cf, "Free Cash Flow")
        if fcf is None:
            capex = value(cf, "Capital Expenditure")
            fcf = ocf + capex if ocf is not None and capex is not None else None
        shares = _safe_float(info.get("sharesOutstanding"), 8)
        previous = _safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
        dividend = _safe_float(info.get("dividendRate"), 8)
        meta = NSE_MASTER_LIST.get(symbol, {})
        quote_time = info.get("regularMarketTime")
        result = {
            "ticker": symbol,
            "original_ticker": ticker,
            "name": info.get("longName") or info.get("shortName") or meta.get("name", symbol),
            "sector": info.get("sector") or meta.get("sector", "Unclassified"),
            "industry": info.get("industry") or meta.get("industry", "Unclassified"),
            "instrument_type": info.get("quoteType", "EQUITY"),
            "isin": info.get("isin"),
            "currency": currency or "INR",
            "website": info.get("website", ""),
            "about": (info.get("longBusinessSummary") or "")[:5000],
            "current_price": price,
            "day_change": round(price - previous, 2) if previous else None,
            "day_change_pct": round((price / previous - 1) * 100, 2) if previous else None,
            "market_cap": _safe_float(info.get("marketCap")),
            "market_cap_cr": _cr(info.get("marketCap")),
            "pe": _safe_float(info.get("trailingPE")),
            "pb": _safe_float(info.get("priceToBook")),
            "eps": _safe_float(info.get("trailingEps")),
            "book_value": _safe_float(info.get("bookValue")),
            "face_value": _safe_float(info.get("faceValue")),
            "week_high_52": _safe_float(info.get("fiftyTwoWeekHigh")),
            "week_low_52": _safe_float(info.get("fiftyTwoWeekLow")),
            "roe": _percent(info.get("returnOnEquity"))
            if info.get("returnOnEquity") is not None
            else (
                round(
                    value(fin, "Net Income")
                    / value(bs, "Total Equity", "Stockholders Equity")
                    * 100,
                    2,
                )
                if value(fin, "Net Income") is not None
                and value(bs, "Stockholders Equity") is not None
                and value(bs, "Stockholders Equity") > 0
                else None
            ),
            "roce": round(ebit / (assets - liabilities) * 100, 2)
            if ebit is not None
            and assets is not None
            and liabilities is not None
            and assets > liabilities
            else None,
            "debt_equity": round(float(info["debtToEquity"]) / 100, 4)
            if _safe_float(info.get("debtToEquity")) is not None
            else None,
            "div_yield": round(dividend / price * 100, 2) if dividend is not None else None,
            "revenue_growth_3yr": _cagr(fin, "Total Revenue", "Operating Revenue"),
            "eps_growth_3yr": _cagr(fin, "Diluted EPS", "Basic EPS"),
            "revenue_growth_yoy": _percent(info.get("revenueGrowth")),
            "earnings_growth_yoy": _percent(info.get("earningsGrowth")),
            "promoter_holding": None,
            "pledged_shares_pct": None,
            "insider_holding": _percent(info.get("heldPercentInsiders")),
            "current_ratio": _safe_float(info.get("currentRatio")),
            "interest_coverage": round(ebit / abs(interest), 2)
            if ebit is not None and interest is not None and interest != 0
            else None,
            "payout_ratio": _percent(info.get("payoutRatio")),
            "operating_cf_debt_ratio": round(ocf / debt, 4)
            if ocf is not None and debt is not None and debt > 0
            else None,
            "free_cash_flow": fcf,
            "shares_outstanding": shares,
            "fcf_per_share": round(fcf / shares, 4)
            if fcf is not None and shares and shares > 0
            else None,
            "financials_as_of": pd.Timestamp(date).date().isoformat() if date is not None else None,
            "quote_as_of": datetime.fromtimestamp(quote_time, timezone.utc).isoformat()
            if isinstance(quote_time, (float, int))
            else None,
            "fetched_at": now_iso(),
            "data_source": "yahoo_finance",
            "delayed_badge": True,
            "source_url": f"https://finance.yahoo.com/quote/{symbol}/",
            "data_note": "Provider quotes may be delayed. Financials may be restated. Insider ownership is not NSE promoter ownership; promoter and pledge data are unavailable.",
        }
        if symbol == "TMPV.NS":
            result["corporate_action_note"] = (
                "TATAMOTORS was renamed TMPV after the 2025 demerger. It is the passenger-vehicle issuer; the commercial-vehicle business is a separate listed company. Pre/post-demerger history is not directly comparable."
            )
            result["corporate_action_source"] = (
                "https://nsearchives.nseindia.com/content/circulars/FAOP70882.pdf"
            )
            result["revenue_growth_3yr"] = None
            result["eps_growth_3yr"] = None
        if symbol == "LTM.NS":
            result["symbol_note"] = "LTIM is now traded as LTM."
        cache_manager.set(key, result, ttl=900)
        return result
    except Exception as exc:
        logger.warning("Profile unavailable for %s: %s", symbol, type(exc).__name__)
        raise MarketDataUnavailable(
            f"Market data unavailable for {symbol}. Verify the symbol or try again later."
        ) from exc


def get_chart_data(
    ticker: str,
    period="1y",
    interval="1d",
    start_date=None,
    end_date=None,
    auto_adjust=True,
):
    symbol = normalize_ticker(ticker)
    if interval not in {"1d", "1wk", "1mo"}:
        raise ValueError("Supported chart intervals: 1d, 1wk, 1mo.")
    if period not in {"1mo", "3mo", "6mo", "1y", "2y", "3y", "5y", "10y", "max"}:
        raise ValueError("Unsupported chart period.")
    key = f"chart_v4:{symbol}:{period}:{interval}:{start_date}:{end_date}:{auto_adjust}"
    cached = cache_manager.get(key)
    if cached:
        return cached
    try:
        kwargs = {
            "interval": interval,
            "auto_adjust": auto_adjust,
            "actions": False,
            "timeout": 12,
        }
        if start_date:
            kwargs["start"] = start_date
            if end_date:
                kwargs["end"] = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).date().isoformat()
        else:
            kwargs["period"] = period
        frame = yf.Ticker(symbol).history(**kwargs)
        bars = []
        for date, row in frame.iterrows():
            vals = [_safe_float(row.get(k), 6) for k in ("Open", "High", "Low", "Close")]
            if any(v is None or v <= 0 for v in vals):
                continue
            volume = _safe_float(row.get("Volume"), 0)
            bars.append(
                dict(
                    time=date.strftime("%Y-%m-%d"),
                    open=vals[0],
                    high=vals[1],
                    low=vals[2],
                    close=vals[3],
                    volume=max(0, int(volume or 0)),
                )
            )
        bars = list({b["time"]: b for b in bars}.values())
        bars.sort(key=lambda b: b["time"])
        result = {
            "ticker": symbol,
            "bars": bars,
            "period": period,
            "interval": interval,
            "data_source": "yahoo_finance" if bars else "unavailable",
            "fetched_at": now_iso(),
            "adjustment": "split_and_dividend_adjusted" if auto_adjust else "provider_close",
            "message": None if bars else "The provider has no price history for this range.",
        }
        cache_manager.set(key, result, ttl=3600 if bars else 60)
        return result
    except Exception as exc:
        logger.warning("Price history unavailable for %s: %s", symbol, type(exc).__name__)
        return {
            "ticker": symbol,
            "bars": [],
            "data_source": "unavailable",
            "message": "Price history temporarily unavailable. Try again later.",
        }


INCOME = [
    ("Total Revenue", "Total Revenue", "Operating Revenue"),
    ("Cost Of Revenue", "Cost Of Revenue"),
    ("Gross Profit", "Gross Profit"),
    ("Operating Income", "Operating Income", "EBIT"),
    ("EBITDA", "EBITDA"),
    ("Net Income", "Net Income", "Net Income Common Stockholders"),
    ("Interest Expense", "Interest Expense"),
    ("Pretax Income", "Pretax Income"),
    ("Tax Provision", "Tax Provision"),
    ("Diluted EPS", "Diluted EPS", "Basic EPS"),
    ("SG&A", "Selling General And Administration"),
    (
        "Depreciation",
        "Reconciled Depreciation",
        "Depreciation And Amortization In Income Statement",
    ),
]
BALANCE = [
    ("Equity Capital", "Common Stock", "Capital Stock"),
    ("Retained Earnings", "Retained Earnings"),
    ("Total Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"),
    ("Total Debt", "Total Debt"),
    ("Current Debt", "Current Debt"),
    ("Long Term Debt", "Long Term Debt"),
    ("Total Liabilities", "Total Liabilities Net Minority Interest"),
    ("Fixed Assets / PPE", "Net PPE"),
    ("Current Assets", "Current Assets"),
    ("Current Liabilities", "Current Liabilities"),
    ("Total Assets", "Total Assets"),
    ("Cash & Equivalents", "Cash And Cash Equivalents"),
    ("Inventory", "Inventory"),
    ("Receivables", "Accounts Receivable", "Receivables"),
    ("Payables", "Accounts Payable", "Payables"),
    ("Shares Outstanding", "Ordinary Shares Number"),
]
CASH = [
    ("Operating Cash Flow", "Operating Cash Flow"),
    ("Capital Expenditure", "Capital Expenditure"),
    ("Free Cash Flow", "Free Cash Flow"),
    ("Investing Cash Flow", "Investing Cash Flow"),
    ("Financing Cash Flow", "Financing Cash Flow"),
    ("Dividends Paid", "Common Stock Dividend Paid"),
    (
        "Depreciation",
        "Depreciation And Amortization",
        "Depreciation Amortization Depletion",
    ),
]


def _statement_rows(frame, dates, mapping):
    rows = []
    for label, *names in mapping:
        raw = [_at(frame, date, *names) for date in dates]
        unit = (
            "₹ / share"
            if label == "Diluted EPS"
            else "shares"
            if label == "Shares Outstanding"
            else "₹ Cr"
        )
        vals = [_safe_float(v, 4) if unit != "₹ Cr" else _cr(v) for v in raw]
        if any(v is not None for v in vals):
            rows.append({"metric": label, "values": vals, "unit": unit})
    return rows


def get_company_financials(ticker: str):
    symbol = normalize_ticker(ticker)
    key = f"financials_v4:{symbol}"
    cached = cache_manager.get(key)
    if cached:
        return cached
    try:
        stock = yf.Ticker(symbol)
        fin, bs, cf = stock.financials, stock.balance_sheet, stock.cashflow
        dates = sorted(set(fin.columns) | set(bs.columns) | set(cf.columns))[-10:]
        result = {
            "ticker": symbol,
            "years": [f"FY{pd.Timestamp(d).strftime('%Y')}" for d in dates],
            "period_dates": [pd.Timestamp(d).date().isoformat() for d in dates],
            "income_statement": _statement_rows(fin, dates, INCOME),
            "balance_sheet": _statement_rows(bs, dates, BALANCE),
            "cash_flow": _statement_rows(cf, dates, CASH),
            "data_source": "yahoo_finance" if dates else "unavailable",
            "fetched_at": now_iso(),
            "basis": "Provider financial statements; standalone/consolidated classification is not supplied.",
        }
        cache_manager.set(key, result, ttl=3600 if dates else 60)
        return result
    except Exception:
        return {
            "ticker": symbol,
            "years": [],
            "period_dates": [],
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
            "data_source": "unavailable",
            "message": "Financial statements temporarily unavailable.",
        }


def financial_value(financials, section, metric, index=-1):
    row = next((r for r in financials.get(section, []) if r["metric"] == metric), None)
    if row is None or not row["values"] or not -len(row["values"]) <= index < len(row["values"]):
        return None
    return _safe_float(row["values"][index], 8)


def get_quarterly_results(ticker: str):
    symbol = normalize_ticker(ticker)
    key = f"quarters_v4:{symbol}"
    cached = cache_manager.get(key)
    if cached:
        return cached
    try:
        frame = yf.Ticker(symbol).quarterly_financials
        dates = sorted(frame.columns)[-12:]
        mapping = [
            ("Sales", "Total Revenue", "Operating Revenue"),
            ("Expenses", "Total Expenses", "Cost Of Revenue"),
            ("Operating Profit", "Operating Income", "EBIT"),
            ("Net Profit", "Net Income"),
            ("Diluted EPS", "Diluted EPS", "Basic EPS"),
        ]
        rows = _statement_rows(frame, dates, mapping)
        sales = [_at(frame, d, "Total Revenue", "Operating Revenue") for d in dates]
        op = [_at(frame, d, "Operating Income", "EBIT") for d in dates]
        rows.append(
            {
                "metric": "OPM %",
                "unit": "%",
                "values": [
                    round(o / s * 100, 2) if s and o is not None else None
                    for s, o in zip(sales, op, strict=True)
                ],
            }
        )
        result = {
            "ticker": symbol,
            "quarters": [pd.Timestamp(d).strftime("%b %Y") for d in dates],
            "period_dates": [pd.Timestamp(d).date().isoformat() for d in dates],
            "rows": rows,
            "data_source": "yahoo_finance" if dates else "unavailable",
            "fetched_at": now_iso(),
        }
        cache_manager.set(key, result, ttl=3600 if dates else 60)
        return result
    except Exception:
        return {
            "ticker": symbol,
            "quarters": [],
            "rows": [],
            "data_source": "unavailable",
            "message": "Quarterly statements temporarily unavailable.",
        }


def get_historical_ratios(ticker: str):
    fin = get_company_financials(ticker)
    rows = []

    def values(section, metric):
        return [financial_value(fin, section, metric, i) for i in range(len(fin["years"]))]

    rev, net, ebit = (
        values("income_statement", m) for m in ("Total Revenue", "Net Income", "Operating Income")
    )
    equity, assets, cl, debt = (
        values("balance_sheet", m)
        for m in ("Total Equity", "Total Assets", "Current Liabilities", "Total Debt")
    )

    def add(label, numerators, denominators, multiplier=100, unit="%"):
        vals = [
            round(a / b * multiplier, 2) if a is not None and b is not None and b > 0 else None
            for a, b in zip(numerators, denominators, strict=True)
        ]
        if any(v is not None for v in vals):
            rows.append({"metric": label, "unit": unit, "values": vals})

    add("OPM %", ebit, rev)
    add("NPM %", net, rev)
    add("ROE %", net, equity)
    add(
        "ROCE %",
        ebit,
        [
            a - c if a is not None and c is not None else None
            for a, c in zip(assets, cl, strict=True)
        ],
    )
    add("Return on Assets %", net, assets)
    add("Debt / Equity", debt, equity, 1, "x")
    add("Operating CF Margin %", values("cash_flow", "Operating Cash Flow"), rev)
    return {
        "ticker": fin["ticker"],
        "years": fin["years"],
        "rows": rows,
        "data_source": fin["data_source"],
        "fetched_at": fin.get("fetched_at"),
        "methodology": "Ratios use matching fiscal periods and year-end balance sheet values.",
    }


def get_company_shareholding(ticker: str):
    profile = get_company_profile(ticker)
    return {
        "ticker": profile["ticker"],
        "quarters": [],
        "breakdown": [],
        "pledged_pct": None,
        "data_source": "unavailable",
        "insider_holding": profile.get("insider_holding"),
        "source_url": "https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
        "message": "Verified NSE promoter, FII, DII and pledge disclosures are not connected. Yahoo insider ownership is not an equivalent substitute.",
    }
