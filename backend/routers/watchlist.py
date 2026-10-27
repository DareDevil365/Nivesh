from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from services.data_fetcher import get_chart_data, get_company_profile, normalize_ticker
from services.indicators import compute_indicators
from services.local_store import connection, workspace

router = APIRouter(tags=["watchlist"])


class AddWatchlistItemRequest(BaseModel):
    watchlist_name: str = Field(default="default", min_length=1, max_length=80)
    ticker: str = Field(min_length=1, max_length=30)


class CreateAlertRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    ticker: str = Field(min_length=1, max_length=30)
    condition: Literal["PRICE_ABOVE", "PRICE_BELOW", "RSI_ABOVE", "RSI_BELOW", "VOLUME_SPIKE"]
    threshold: float = Field(ge=0, le=1e12)


def enrich(item):
    base = dict(item)
    try:
        profile = get_company_profile(base["ticker"])
        return {
            **base,
            **{
                key: profile.get(key)
                for key in (
                    "name",
                    "sector",
                    "current_price",
                    "day_change",
                    "day_change_pct",
                    "pe",
                    "roe",
                    "quote_as_of",
                    "fetched_at",
                )
            },
            "available": True,
        }
    except ValueError:
        return {
            **base,
            "name": base["ticker"],
            "sector": "Unavailable",
            "current_price": None,
            "day_change": None,
            "day_change_pct": None,
            "pe": None,
            "roe": None,
            "available": False,
        }


@router.get("/api/watchlist")
def get_watchlist(name: str = "default", owner=Depends(workspace)):
    with connection() as db:
        items = db.execute(
            "SELECT ticker, added_at FROM watchlist WHERE owner=? AND name=? ORDER BY added_at DESC",
            (owner, name),
        ).fetchall()
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(enrich, items))
    return {
        "name": name,
        "count": len(result),
        "items": result,
        "storage": "Saved in this browser's workspace. Clearing cookies loses access. No cross-device account sync.",
    }


@router.post("/api/watchlist/item")
def add_watchlist_item(req: AddWatchlistItemRequest, owner=Depends(workspace)):
    try:
        ticker = normalize_ticker(req.ticker)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with connection() as db:
        count = db.execute("SELECT COUNT(*) FROM watchlist WHERE owner=?", (owner,)).fetchone()[0]
        if count >= 200:
            raise HTTPException(409, "Workspace watchlist limit is 200 stocks.")
        cursor = db.execute(
            "INSERT OR IGNORE INTO watchlist VALUES(?,?,?,?)",
            (owner, req.watchlist_name, ticker, datetime.now(timezone.utc).isoformat()),
        )
    return {"status": "added" if cursor.rowcount else "exists", "ticker": ticker}


@router.delete("/api/watchlist/item")
def remove_watchlist_item(ticker: str, name: str = "default", owner=Depends(workspace)):
    try:
        ticker = normalize_ticker(ticker)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with connection() as db:
        db.execute(
            "DELETE FROM watchlist WHERE owner=? AND name=? AND ticker=?",
            (owner, name, ticker),
        )
    return {"status": "removed", "ticker": ticker}


@router.get("/api/alerts")
@router.get("/api/watchlist/alerts")
def get_alerts(owner=Depends(workspace)):
    with connection() as db:
        rows = db.execute(
            "SELECT id,ticker,condition,threshold,created_at FROM alerts WHERE owner=? ORDER BY created_at DESC",
            (owner,),
        ).fetchall()
    result = []
    profiles, charts = {}, {}
    for row in rows:
        alert = dict(row)
        ticker = alert["ticker"]
        observed, checked_at = None, None
        try:
            if ticker not in profiles:
                profiles[ticker] = get_company_profile(ticker)
            profile = profiles[ticker]
            checked_at = profile.get("quote_as_of") or profile.get("fetched_at")
            if alert["condition"].startswith("PRICE"):
                observed = profile.get("current_price")
            else:
                if ticker not in charts:
                    bars = get_chart_data(ticker).get("bars", [])
                    charts[ticker] = (
                        compute_indicators(pd.DataFrame(bars)) if bars else pd.DataFrame()
                    )
                chart = charts[ticker]
                if not chart.empty:
                    last = chart.iloc[-1]
                    checked_at = str(last["time"])
                    if alert["condition"].startswith("RSI"):
                        observed = float(last["RSI_14"]) if pd.notna(last["RSI_14"]) else None
                    elif pd.notna(last["VOL_SMA_20"]) and last["VOL_SMA_20"] > 0:
                        observed = float(last["volume"] / last["VOL_SMA_20"])
        except (ValueError, KeyError):
            pass
        above = alert["condition"] in {"PRICE_ABOVE", "RSI_ABOVE", "VOLUME_SPIKE"}
        triggered = (
            (observed >= alert["threshold"] if above else observed <= alert["threshold"])
            if observed is not None
            else None
        )
        result.append(
            {
                **alert,
                "active": True,
                "triggered": triggered,
                "observed_value": observed,
                "checked_at": checked_at,
            }
        )
    return {
        "alerts": result,
        "evaluation": "Conditions are evaluated when this page is refreshed. No background notifications are sent.",
    }


@router.post("/api/alerts")
@router.post("/api/watchlist/alerts")
def create_alert(req: CreateAlertRequest, owner=Depends(workspace)):
    if not req.condition.startswith("RSI") and req.threshold <= 0:
        raise HTTPException(422, "Price and volume thresholds must be positive.")
    if req.condition.startswith("RSI") and req.threshold > 100:
        raise HTTPException(422, "RSI threshold must be between 0 and 100.")
    try:
        ticker = normalize_ticker(req.ticker)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    alert = {
        "id": str(uuid4()),
        "ticker": ticker,
        "condition": req.condition,
        "threshold": req.threshold,
        "active": True,
    }
    with connection() as db:
        if db.execute("SELECT COUNT(*) FROM alerts WHERE owner=?", (owner,)).fetchone()[0] >= 30:
            raise HTTPException(409, "Workspace alert limit is 30.")
        db.execute(
            "INSERT INTO alerts VALUES(?,?,?,?,?,?)",
            (
                alert["id"],
                owner,
                ticker,
                req.condition,
                req.threshold,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return {"status": "created", "alert": alert}


@router.delete("/api/watchlist/alerts/{alert_id}")
def delete_alert(alert_id: str, owner=Depends(workspace)):
    with connection() as db:
        db.execute("DELETE FROM alerts WHERE id=? AND owner=?", (alert_id, owner))
    return {"status": "removed"}
