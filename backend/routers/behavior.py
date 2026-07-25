from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from services.behavior_engine import analyze_trade_behavior

router = APIRouter(prefix="/api/behavior", tags=["behavior"])

SAMPLE_TRADES = [
    {"ticker": "RELIANCE.NS", "buy_date": "2026-01-05", "buy_price": 2800.0, "sell_date": "2026-01-20", "sell_price": 2950.0, "qty": 50},
    {"ticker": "TCS.NS", "buy_date": "2026-01-10", "buy_price": 3900.0, "sell_date": "2026-02-15", "sell_price": 3700.0, "qty": 30},
    {"ticker": "INFY.NS", "buy_date": "2026-01-15", "buy_price": 1600.0, "sell_date": "2026-01-18", "sell_price": 1650.0, "qty": 100},
    {"ticker": "TATAMOTORS.NS", "buy_date": "2026-02-01", "buy_price": 950.0, "sell_date": "2026-03-10", "sell_price": 880.0, "qty": 80},
    {"ticker": "HDFCBANK.NS", "buy_date": "2026-02-16", "buy_price": 1420.0, "sell_date": "2026-02-18", "sell_price": 1460.0, "qty": 70},
    {"ticker": "ICICIBANK.NS", "buy_date": "2026-02-19", "buy_price": 1050.0, "sell_date": "2026-03-25", "sell_price": 980.0, "qty": 90},
]

class AnalyzeBehaviorRequest(BaseModel):
    trades: Optional[List[Dict[str, Any]]] = None

@router.post("/upload")
def upload_trade_csv(req: AnalyzeBehaviorRequest):
    trade_list = req.trades if req.trades else SAMPLE_TRADES
    return {"status": "uploaded", "trade_count": len(trade_list), "trades": trade_list}

@router.post("/analyze")
def analyze_behavior(req: AnalyzeBehaviorRequest):
    trade_list = req.trades if req.trades else SAMPLE_TRADES
    analysis = analyze_trade_behavior(trade_list)

    # Generated Narrated Advice Paragraph
    disp = analysis["metrics"]["disposition_effect_score"]
    la = analysis["metrics"]["loss_aversion_ratio"]

    narrative = (
        f"You tend to hold losing positions {disp}x longer than winning ones, exhibiting a classic disposition effect. "
        f"Your average loss is {la}x larger than your average gain. Setting disciplined, automated stop-losses before entering trades "
        f"will help protect your overall portfolio expectancy."
    )

    return {
        "metrics": analysis["metrics"],
        "flags": analysis["flags"],
        "narrative": narrative
    }
