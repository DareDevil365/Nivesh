"""Persistent research snapshot. Refreshes the full bundled universe in a bounded worker."""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from services.data_fetcher import get_company_profile, normalize_ticker
from services.local_store import connection
from services.nse_stock_master import NSE_MASTER_LIST
from services.snowflake_calculator import compute_snowflake_scores

NSE_UNIVERSE = list(dict.fromkeys(normalize_ticker(symbol) for symbol in NSE_MASTER_LIST))
PRESET_SCREENS = {
    "quality_compounders": {
        "name": "Quality Compounders",
        "description": "High ROE & ROCE companies with low debt and steady growth",
        "filters": {
            "min_roe": 15.0,
            "min_roce": 15.0,
            "max_debt_equity": 0.5,
            "min_revenue_growth": 10.0,
        },
    },
    "deep_value": {
        "name": "Deep Value",
        "description": "Stocks trading at attractive P/E and P/B valuation multiples",
        "filters": {"max_pe": 20.0, "max_pb": 3.0, "min_div_yield": 1.0},
    },
    "high_dividend": {
        "name": "High Dividend Yield",
        "description": "Companies providing generous dividend payouts with strong profitability",
        "filters": {"min_div_yield": 1.5, "min_roe": 10.0},
    },
    "low_debt_growth": {
        "name": "Low Debt + High Growth",
        "description": "Virtually debt-free companies expanding profits rapidly",
        "filters": {"max_debt_equity": 0.15, "min_eps_growth": 12.0},
    },
    "zero_pledge": {
        "name": "Zero Promoter Pledge",
        "description": "Clean promoter ownership with zero pledged shares",
        "filters": {"max_pledged": 0.0, "min_promoter": 45.0},
    },
    "sector_leaders": {
        "name": "Sector Leaders",
        "description": "Large-cap industry market leaders with robust ROCE",
        "filters": {"min_market_cap": 500000000000, "min_roce": 14.0},
    },
    "garp": {
        "name": "GARP (Growth at Reasonable Price)",
        "description": "Reasonable valuation combined with solid profit growth",
        "filters": {"max_pe": 30.0, "min_eps_growth": 12.0, "min_roe": 14.0},
    },
    "cash_flow_kings": {
        "name": "Cash Flow Kings",
        "description": "Highly capital efficient businesses generating surplus returns",
        "filters": {
            "min_roce": 18.0,
            "max_debt_equity": 0.4,
            "min_free_cash_flow": 0.01,
        },
    },
}


_refresh_lock = threading.Lock()
_refreshing = False
_last_attempt = 0.0
_last_error_count = 0


def fetch_single_profile(ticker):
    try:
        profile = get_company_profile(ticker)
        scores = compute_snowflake_scores(profile)
        profile = {
            **profile,
            "snowflake_total": scores["total"],
            "snowflake_score": scores["total"],
            "snowflake_scores": scores,
        }
        with connection() as db:
            db.execute(
                "INSERT OR REPLACE INTO market_snapshots VALUES(?,?,?)",
                (profile["ticker"], json.dumps(profile, allow_nan=False), time.time()),
            )
        return profile
    except Exception:
        return None


def _refresh():
    global _refreshing, _last_error_count
    failed = 0
    try:
        # One bounded batch at a time. Avoid flooding a provider during an outage.
        for offset in range(0, len(NSE_UNIVERSE), 12):
            with ThreadPoolExecutor(max_workers=4) as pool:
                batch = list(pool.map(fetch_single_profile, NSE_UNIVERSE[offset : offset + 12]))
            failed += sum(p is None for p in batch)
            if offset == 0 and all(p is None for p in batch):
                break
        _last_error_count = failed
    finally:
        with _refresh_lock:
            _refreshing = False


def refresh_snapshot(force=False):
    global _refreshing, _last_attempt
    with _refresh_lock:
        if _refreshing or time.time() - _last_attempt < (60 if force else 3600):
            return
        _refreshing = True
        _last_attempt = time.time()
    threading.Thread(target=_refresh, daemon=True, name="nivesh-market-refresh").start()


def snapshot(refresh=True):
    with connection() as db:
        stored = db.execute("SELECT payload,updated_at FROM market_snapshots").fetchall()
    stocks = [json.loads(row["payload"]) for row in stored]
    universe = set(NSE_UNIVERSE)
    stocks = [p for p in stocks if p["ticker"] in universe]
    if refresh and (
        len(stocks) < len(NSE_UNIVERSE)
        or any(time.time() - row["updated_at"] > 3600 for row in stored)
    ):
        refresh_snapshot()
    oldest = min((p.get("fetched_at", "") for p in stocks), default=None)
    newest = max((p.get("fetched_at", "") for p in stocks), default=None)
    coverage = {
        "covered": len(stocks),
        "universe": len(NSE_UNIVERSE),
        "refreshing": _refreshing,
        "oldest_fetched_at": oldest,
        "newest_fetched_at": newest,
        "failed_last_refresh": _last_error_count,
        "scope": "Bundled research universe; not every NSE listing.",
        "stale": any(time.time() - row["updated_at"] > 3600 for row in stored),
    }
    return stocks, coverage


def get_all_screener_stocks(limit=None):
    stocks, _ = snapshot()
    return stocks if limit is None else stocks[:limit]


def filter_stocks(filters):
    stocks, _ = snapshot()
    result = []
    comparisons = {
        "min_pe": ("pe", True),
        "max_pe": ("pe", False),
        "min_pb": ("pb", True),
        "max_pb": ("pb", False),
        "min_roe": ("roe", True),
        "min_roce": ("roce", True),
        "max_debt_equity": ("debt_equity", False),
        "min_div_yield": ("div_yield", True),
        "min_revenue_growth": ("revenue_growth_3yr", True),
        "min_eps_growth": ("eps_growth_3yr", True),
        "min_promoter": ("promoter_holding", True),
        "max_pledged": ("pledged_shares_pct", False),
        "min_free_cash_flow": ("free_cash_flow", True),
        "min_market_cap": ("market_cap", True),
        "max_market_cap": ("market_cap", False),
    }
    for stock in stocks:
        if filters.get("sector") and stock.get("sector", "").lower() != filters["sector"].lower():
            continue
        matches = True
        for parameter, (metric, is_min) in comparisons.items():
            if filters.get(parameter) is None:
                continue
            value = stock.get(metric)
            if value is None or (
                value < float(filters[parameter]) if is_min else value > float(filters[parameter])
            ):
                matches = False
                break
        if matches:
            result.append(stock)
    field = filters.get("sort_by", "market_cap")
    if field not in {
        "market_cap",
        "pe",
        "pb",
        "roe",
        "roce",
        "debt_equity",
        "div_yield",
        "snowflake_total",
    }:
        field = "market_cap"
    present = [p for p in result if p.get(field) is not None]
    missing = [p for p in result if p.get(field) is None]
    present.sort(
        key=lambda p: (p[field], p["ticker"]),
        reverse=filters.get("order", "desc") == "desc",
    )
    return present + missing


def get_peers(ticker):
    profile = get_company_profile(ticker)
    stocks, _ = snapshot()
    # Never fill an empty peer list with unrelated industries.
    peers = [
        p
        for p in stocks
        if p["ticker"] != profile["ticker"] and p.get("industry") == profile.get("industry")
    ]
    peers.sort(key=lambda p: p.get("market_cap") or 0, reverse=True)
    return [dict(profile, snowflake_score=compute_snowflake_scores(profile)["total"])] + peers[:12]


def get_sector_heatmap():
    stocks, _ = snapshot()
    sectors = {}
    for stock in stocks:
        cap, change = stock.get("market_cap"), stock.get("day_change_pct")
        if cap is None or cap <= 0 or change is None:
            continue
        sector = stock.get("sector") or "Unclassified"
        item = sectors.setdefault(
            sector,
            {
                "sector": sector,
                "total_market_cap": 0,
                "weighted": 0,
                "stock_count": 0,
                "top_stocks": [],
            },
        )
        item["total_market_cap"] += cap
        item["weighted"] += cap * change
        item["stock_count"] += 1
        item["top_stocks"].append(
            {"ticker": stock["ticker"], "name": stock["name"], "change_pct": change}
        )
    result = []
    for item in sectors.values():
        item["avg_change_pct"] = round(item.pop("weighted") / item["total_market_cap"], 2)
        item["top_stocks"] = item["top_stocks"][:4]
        result.append(item)
    return sorted(result, key=lambda p: p["total_market_cap"], reverse=True)
