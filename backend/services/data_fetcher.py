import time
import logging
from typing import Dict, Any, Optional
import yfinance as yf
from services.cache_manager import cache_manager
from services.nse_stock_master import resolve_symbol_alias, NSE_MASTER_LIST

logger = logging.getLogger(__name__)

def normalize_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    ticker = resolve_symbol_alias(ticker)
    if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
        ticker = f"{ticker}.NS"
    return resolve_symbol_alias(ticker)

def get_company_profile(ticker: str) -> Dict[str, Any]:
    resolved_ticker = normalize_ticker(ticker)
    cache_key = f"company_profile:{resolved_ticker}"
    
    # Check cache first
    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    master_meta = NSE_MASTER_LIST.get(resolved_ticker, {})
    name = master_meta.get("name", resolved_ticker.replace(".NS", "").replace(".BO", ""))
    sector = master_meta.get("sector", "NSE Equity")
    industry = master_meta.get("industry", "General Equity")

    # Fetch live data strictly from yfinance
    try:
        yf_ticker = yf.Ticker(resolved_ticker)
        info = yf_ticker.info or {}

        # If info is empty, try raw ticker without .NS or alternative
        if not info or (not info.get("shortName") and not info.get("longName") and not info.get("regularMarketPrice") and not info.get("currentPrice")):
            # Try secondary lookup
            alt_ticker = resolved_ticker.replace(".NS", "")
            alt_info = yf.Ticker(alt_ticker).info or {}
            if alt_info and (alt_info.get("shortName") or alt_info.get("longName") or alt_info.get("regularMarketPrice")):
                info = alt_info

        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or info.get("open")
        
        # If no live price or profile info exists on exchange/yfinance, deny request (no bogus data)
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
        market_cap_cr = round(market_cap / 10000000.0, 2) if mcap else 0.0

        pe = round(float(info["trailingPE"]), 2) if info.get("trailingPE") else None
        pb = round(float(info["priceToBook"]), 2) if info.get("priceToBook") else None

        roe_raw = info.get("returnOnEquity")
        roe = round(float(roe_raw) * 100 if abs(roe_raw) < 1.0 else float(roe_raw), 2) if roe_raw is not None else None

        # ROCE Calculation: EBIT / (Total Assets - Current Liabilities) from real financial statements
        roce = None
        try:
            financials = yf_ticker.financials
            balance_sheet = yf_ticker.balance_sheet
            if financials is not None and not financials.empty and balance_sheet is not None and not balance_sheet.empty:
                ebit = financials.loc["EBIT"].iloc[0] if "EBIT" in financials.index else None
                total_assets = balance_sheet.loc["Total Assets"].iloc[0] if "Total Assets" in balance_sheet.index else None
                curr_liab = balance_sheet.loc["Current Liabilities"].iloc[0] if "Current Liabilities" in balance_sheet.index else 0
                if ebit and total_assets and (total_assets - curr_liab) > 0:
                    roce = round(float(ebit / (total_assets - curr_liab)) * 100, 2)
        except Exception:
            roce = None

        if roce is None and roe is not None:
            roce = roe  # Fall back to ROE if ROCE statement unavailable

        de_raw = info.get("debtToEquity")
        debt_equity = round(float(de_raw) / 100.0 if de_raw > 5.0 else float(de_raw), 2) if de_raw is not None else None

        dy_raw = info.get("dividendYield")
        div_yield = round(float(dy_raw) * 100 if dy_raw < 0.5 else float(dy_raw), 2) if dy_raw is not None else 0.0

        insider_pct = info.get("heldPercentInsiders")
        promoter_holding = round(float(insider_pct) * 100, 2) if insider_pct is not None else None

        profile_data = {
            "ticker": resolved_ticker,
            "original_ticker": ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "isin": isin,
            "current_price": current_price,
            "day_change": day_change,
            "day_change_pct": day_change_pct,
            "market_cap": market_cap,
            "market_cap_cr": market_cap_cr,
            "pe": pe,
            "pb": pb,
            "roe": roe,
            "roce": roce,
            "debt_equity": debt_equity,
            "div_yield": div_yield,
            "revenue_growth_3yr": round(float(info.get("revenueGrowth", 0.0)) * 100, 2) if info.get("revenueGrowth") else None,
            "eps_growth_3yr": round(float(info.get("earningsGrowth", 0.0)) * 100, 2) if info.get("earningsGrowth") else None,
            "promoter_holding": promoter_holding,
            "pledged_shares_pct": 0.0,
            "current_ratio": round(float(info["currentRatio"]), 2) if info.get("currentRatio") else None,
            "interest_coverage": None,
            "payout_ratio": round(float(info["payoutRatio"]) * 100, 2) if info.get("payoutRatio") else None,
            "operating_cf_debt_ratio": None,
            "data_source": "live",
            "delayed_badge": True
        }

        # Cache profile for 15 minutes (900 seconds)
        cache_manager.set(cache_key, profile_data, ttl=900)
        return profile_data

    except Exception as e:
        logger.warning(f"Live data fetch failed for {ticker} ({resolved_ticker}): {e}")
        raise ValueError(f"Real-time market data unavailable for ticker '{ticker}'. Error: {str(e)}")

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
            # Try raw ticker
            alt_ticker = resolved_ticker.replace(".NS", "")
            df = yf.Ticker(alt_ticker).history(period=period, interval=interval)

        if df.empty:
            return {
                "ticker": resolved_ticker,
                "period": period,
                "interval": interval,
                "bars": [],
                "error": f"No price history returned for {ticker}",
                "data_source": "unavailable"
            }

        bars = []
        for index, row in df.iterrows():
            date_str = index.strftime("%Y-%m-%d")
            bars.append({
                "time": date_str,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"])
            })

        chart_result = {
            "ticker": resolved_ticker,
            "period": period,
            "interval": interval,
            "bars": bars,
            "data_source": "live"
        }
        
        ttl = 3600 if interval == "1d" else 300
        cache_manager.set(cache_key, chart_result, ttl=ttl)
        return chart_result

    except Exception as e:
        logger.warning(f"Failed to fetch live chart for {ticker}: {e}")
        return {
            "ticker": resolved_ticker,
            "period": period,
            "interval": interval,
            "bars": [],
            "error": f"Failed to fetch price data for {ticker}",
            "data_source": "unavailable"
        }

def get_company_financials(ticker: str) -> Dict[str, Any]:
    resolved_ticker = normalize_ticker(ticker)
    cache_key = f"financials:{resolved_ticker}"
    
    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    try:
        yf_ticker = yf.Ticker(resolved_ticker)
        fin = yf_ticker.financials
        bs = yf_ticker.balance_sheet
        cf = yf_ticker.cashflow
        
        income_rows = []
        years = []
        if fin is not None and not fin.empty:
            cols = [col.strftime("%Y") for col in fin.columns[:5]]
            years = [f"FY{c[-2:]}" for c in cols[::-1]]
            
            for item_name in ["Total Revenue", "EBITDA", "Net Income", "Operating Income"]:
                if item_name in fin.index:
                    vals = [round(float(v)/10000000.0, 2) for v in fin.loc[item_name].values[:5][::-1]]
                    income_rows.append({"metric": item_name, "values": vals})
        
        bs_rows = []
        if bs is not None and not bs.empty:
            for item_name in ["Total Assets", "Total Debt", "Stockholders Equity"]:
                if item_name in bs.index:
                    vals = [round(float(v)/10000000.0, 2) for v in bs.loc[item_name].values[:5][::-1]]
                    bs_rows.append({"metric": item_name, "values": vals})

        cf_rows = []
        if cf is not None and not cf.empty:
            for item_name in ["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow"]:
                if item_name in cf.index:
                    vals = [round(float(v)/10000000.0, 2) for v in cf.loc[item_name].values[:5][::-1]]
                    cf_rows.append({"metric": item_name, "values": vals})

        if not income_rows and not bs_rows:
            return {
                "ticker": resolved_ticker,
                "years": [],
                "income_statement": [],
                "balance_sheet": [],
                "cash_flow": [],
                "data_source": "unavailable",
                "message": "Historical financial statements unavailable from exchange provider."
            }

        res = {
            "ticker": resolved_ticker,
            "years": years,
            "income_statement": income_rows,
            "balance_sheet": bs_rows,
            "cash_flow": cf_rows,
            "data_source": "live"
        }
        cache_manager.set(cache_key, res, ttl=3600)
        return res
    except Exception as e:
        logger.warning(f"Financials fetch failed for {ticker}: {e}")
        return {
            "ticker": resolved_ticker,
            "years": [],
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
            "data_source": "unavailable",
            "message": "Historical financial statements unavailable."
        }

def get_company_shareholding(ticker: str) -> Dict[str, Any]:
    resolved_ticker = normalize_ticker(ticker)
    cache_key = f"shareholding:{resolved_ticker}"
    
    cached = cache_manager.get(cache_key)
    if cached:
        return cached

    try:
        yf_ticker = yf.Ticker(resolved_ticker)
        info = yf_ticker.info or {}
        
        insider_pct = info.get("heldPercentInsiders")
        inst_pct = info.get("heldPercentInstitutions")

        if insider_pct is not None or inst_pct is not None:
            promoter = round(float(insider_pct) * 100, 2) if insider_pct is not None else 0.0
            institutions = round(float(inst_pct) * 100, 2) if inst_pct is not None else 0.0
            public = round(max(0.0, 100.0 - (promoter + institutions)), 2)

            res = {
                "ticker": resolved_ticker,
                "quarters": ["Latest"],
                "breakdown": [
                    {"category": "Promoter & Insiders", "pct": promoter, "trend": [promoter]},
                    {"category": "Institutional Holdings", "pct": institutions, "trend": [institutions]},
                    {"category": "Public & Others", "pct": public, "trend": [public]}
                ],
                "pledged_pct": 0.0,
                "data_source": "live"
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


