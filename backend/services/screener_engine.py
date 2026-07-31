from typing import Dict, Any, List, Optional
from services.data_fetcher import get_company_profile
from services.nse_stock_master import NSE_MASTER_LIST
from services.snowflake_calculator import compute_snowflake_scores

# Universe of NSE stocks for stock screener
NSE_UNIVERSE = list(NSE_MASTER_LIST.keys())

PRESET_SCREENS = {
    "quality_compounders": {
        "name": "Quality Compounders",
        "description": "High ROE & ROCE companies with low debt and steady growth",
        "filters": {"min_roe": 15.0, "min_roce": 15.0, "max_debt_equity": 0.5, "min_revenue_growth": 10.0}
    },
    "deep_value": {
        "name": "Deep Value",
        "description": "Stocks trading at attractive P/E and P/B valuation multiples",
        "filters": {"max_pe": 20.0, "max_pb": 3.0, "min_div_yield": 1.0}
    },
    "high_dividend": {
        "name": "High Dividend Yield",
        "description": "Companies providing generous dividend payouts with strong profitability",
        "filters": {"min_div_yield": 1.5, "min_roe": 10.0}
    },
    "low_debt_growth": {
        "name": "Low Debt + High Growth",
        "description": "Virtually debt-free companies expanding profits rapidly",
        "filters": {"max_debt_equity": 0.15, "min_eps_growth": 12.0}
    },
    "zero_pledge": {
        "name": "Zero Promoter Pledge",
        "description": "Clean promoter ownership with zero pledged shares",
        "filters": {"max_pledged": 0.0, "min_promoter": 45.0}
    },
    "sector_leaders": {
        "name": "Sector Leaders",
        "description": "Large-cap industry market leaders with robust ROCE",
        "filters": {"min_market_cap": 500000000000, "min_roce": 14.0}
    },
    "garp": {
        "name": "GARP (Growth at Reasonable Price)",
        "description": "Reasonable valuation combined with solid profit growth",
        "filters": {"max_pe": 30.0, "min_eps_growth": 12.0, "min_roe": 14.0}
    },
    "cash_flow_kings": {
        "name": "Cash Flow Kings",
        "description": "Highly capital efficient businesses generating surplus returns",
        "filters": {"min_roce": 18.0, "max_debt_equity": 0.4}
    }
}

def fetch_single_profile(ticker: str) -> Optional[Dict[str, Any]]:
    try:
        profile = get_company_profile(ticker)
        scores = compute_snowflake_scores(profile)
        profile["snowflake_total"] = scores["total"]
        profile["snowflake_scores"] = scores
        return profile
    except Exception:
        return None

def get_all_screener_stocks(limit: int = 60) -> List[Dict[str, Any]]:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    stocks = []
    target_universe = NSE_UNIVERSE[:limit]
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_profile, ticker) for ticker in target_universe]
        for future in as_completed(futures):
            res = future.result()
            if res is not None:
                stocks.append(res)
                
    return stocks

def filter_stocks(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    all_stocks = get_all_screener_stocks()
    filtered = []

    min_pe = filters.get("min_pe")
    max_pe = filters.get("max_pe")
    min_pb = filters.get("min_pb")
    max_pb = filters.get("max_pb")
    min_roe = filters.get("min_roe")
    min_roce = filters.get("min_roce")
    max_debt_equity = filters.get("max_debt_equity")
    min_div_yield = filters.get("min_div_yield")
    min_rev_growth = filters.get("min_revenue_growth")
    min_eps_growth = filters.get("min_eps_growth")
    min_promoter = filters.get("min_promoter")
    max_pledged = filters.get("max_pledged")
    min_market_cap = filters.get("min_market_cap")
    max_market_cap = filters.get("max_market_cap")
    sector_filter = filters.get("sector")

    sort_by = filters.get("sort_by", "market_cap")
    order = filters.get("order", "desc")

    for s in all_stocks:
        f = s

        if sector_filter and (s.get("sector") or "").lower() != sector_filter.lower():
            continue
        if min_pe is not None and (f.get("pe") is None or f["pe"] < float(min_pe)):
            continue
        if max_pe is not None and (f.get("pe") is None or f["pe"] > float(max_pe)):
            continue
        if min_pb is not None and (f.get("pb") is None or f["pb"] < float(min_pb)):
            continue
        if max_pb is not None and (f.get("pb") is None or f["pb"] > float(max_pb)):
            continue
        if min_roe is not None and (f.get("roe") is None or f["roe"] < float(min_roe)):
            continue
        if min_roce is not None and (f.get("roce") is None or f["roce"] < float(min_roce)):
            continue
        if max_debt_equity is not None and (f.get("debt_equity") is None or f["debt_equity"] > float(max_debt_equity)):
            continue
        if min_div_yield is not None and (f.get("div_yield") or 0.0) < float(min_div_yield):
            continue
        if min_rev_growth is not None and (f.get("revenue_growth_3yr") or 0.0) < float(min_rev_growth):
            continue
        if min_eps_growth is not None and (f.get("eps_growth_3yr") or 0.0) < float(min_eps_growth):
            continue
        if min_promoter is not None and (f.get("promoter_holding") or 0.0) < float(min_promoter):
            continue
        if max_pledged is not None and (f.get("pledged_shares_pct") or 0.0) > float(max_pledged):
            continue
        if min_market_cap is not None and (f.get("market_cap") or 0.0) < float(min_market_cap):
            continue
        if max_market_cap is not None and (f.get("market_cap") or 0.0) > float(max_market_cap):
            continue

        filtered.append(s)

    # Sorting
    reverse_sort = (order == "desc")
    if sort_by in ["market_cap", "pe", "pb", "roe", "roce", "debt_equity", "div_yield", "snowflake_total"]:
        filtered.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse_sort)

    return filtered

def get_peers(ticker: str) -> List[Dict[str, Any]]:
    profile = get_company_profile(ticker)
    target_sector = profile["sector"]
    all_stocks = get_all_screener_stocks()

    peers = [s for s in all_stocks if s["sector"] == target_sector and s["ticker"] != profile["ticker"]]
    if not peers:
        peers = [s for s in all_stocks if s["ticker"] != profile["ticker"]][:4]

    return peers

def get_sector_heatmap() -> List[Dict[str, Any]]:
    all_stocks = get_all_screener_stocks()
    sectors: Dict[str, Dict[str, Any]] = {}

    for s in all_stocks:
        sec = s["sector"]
        if sec not in sectors:
            sectors[sec] = {
                "sector": sec,
                "total_market_cap": 0,
                "weighted_day_change_sum": 0.0,
                "stock_count": 0,
                "stocks": []
            }
        mcap = s.get("market_cap", 0.0) or 0.0
        change = s.get("day_change_pct", 0.0) or 0.0
        sectors[sec]["total_market_cap"] += mcap
        sectors[sec]["weighted_day_change_sum"] += change * mcap
        sectors[sec]["stock_count"] += 1
        sectors[sec]["stocks"].append({"ticker": s["ticker"], "name": s["name"], "change_pct": change})

    result = []
    for sec, data in sectors.items():
        mcap_total = data["total_market_cap"]
        avg_change = (data["weighted_day_change_sum"] / mcap_total) if mcap_total > 0 else 0.0
        result.append({
            "sector": sec,
            "total_market_cap": mcap_total,
            "avg_change_pct": round(avg_change, 2),
            "stock_count": data["stock_count"],
            "top_stocks": data["stocks"][:4]
        })

    result.sort(key=lambda x: x["total_market_cap"], reverse=True)
    return result
