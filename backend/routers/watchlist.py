from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services.data_fetcher import get_company_profile

router = APIRouter(tags=["watchlist"])

USER_WATCHLISTS = {
    "default": [
        {"ticker": "RELIANCE.NS", "added_at": "2026-07-25T10:00:00Z"},
        {"ticker": "TCS.NS", "added_at": "2026-07-25T10:00:00Z"},
        {"ticker": "INFY.NS", "added_at": "2026-07-25T10:00:00Z"},
        {"ticker": "HDFCBANK.NS", "added_at": "2026-07-25T10:00:00Z"}
    ]
}

USER_ALERTS = [
    {"id": "alert-1", "ticker": "RELIANCE.NS", "condition": "PRICE_ABOVE", "threshold": 3100.0, "active": True},
    {"id": "alert-2", "ticker": "TCS.NS", "condition": "RSI_BELOW", "threshold": 30.0, "active": True}
]

class AddWatchlistItemRequest(BaseModel):
    watchlist_name: str = "default"
    ticker: str

class CreateAlertRequest(BaseModel):
    ticker: str
    condition: str  # PRICE_ABOVE, PRICE_BELOW, RSI_ABOVE, RSI_BELOW, VOLUME_SPIKE
    threshold: float

@router.get("/api/watchlist")
def get_watchlist(name: str = "default"):
    items = USER_WATCHLISTS.get(name, [])
    enriched_items = []
    for item in items:
        try:
            profile = get_company_profile(item["ticker"])
            enriched_items.append({
                "ticker": item["ticker"],
                "added_at": item["added_at"],
                "name": profile["name"],
                "sector": profile["sector"],
                "current_price": profile["fundamentals"]["current_price"],
                "day_change": profile["fundamentals"]["day_change"],
                "day_change_pct": profile["fundamentals"]["day_change_pct"],
                "pe": profile["fundamentals"]["pe"],
                "roe": profile["fundamentals"]["roe"]
            })
        except Exception:
            continue

    return {"name": name, "count": len(enriched_items), "items": enriched_items}

@router.post("/api/watchlist/item")
def add_watchlist_item(req: AddWatchlistItemRequest):
    ticker = req.ticker.upper().strip()
    if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
        ticker = f"{ticker}.NS"

    name = req.watchlist_name
    if name not in USER_WATCHLISTS:
        USER_WATCHLISTS[name] = []

    for existing in USER_WATCHLISTS[name]:
        if existing["ticker"] == ticker:
            return {"status": "exists", "ticker": ticker}

    USER_WATCHLISTS[name].append({"ticker": ticker, "added_at": "2026-07-25T12:00:00Z"})
    return {"status": "added", "ticker": ticker, "watchlist": name}

@router.delete("/api/watchlist/item")
def remove_watchlist_item(ticker: str, name: str = "default"):
    ticker_clean = ticker.upper().strip()
    if name in USER_WATCHLISTS:
        USER_WATCHLISTS[name] = [item for item in USER_WATCHLISTS[name] if item["ticker"] != ticker_clean]
    return {"status": "removed", "ticker": ticker_clean}

@router.get("/api/alerts")
@router.get("/api/watchlist/alerts")
def get_alerts():
    return {"alerts": USER_ALERTS}

@router.post("/api/alerts")
@router.post("/api/watchlist/alerts")
def create_alert(req: CreateAlertRequest):
    alert_id = f"alert-{len(USER_ALERTS) + 1}"
    new_alert = {
        "id": alert_id,
        "ticker": req.ticker.upper().strip(),
        "condition": req.condition,
        "threshold": req.threshold,
        "active": True
    }
    USER_ALERTS.append(new_alert)
    return {"status": "created", "alert": new_alert}
