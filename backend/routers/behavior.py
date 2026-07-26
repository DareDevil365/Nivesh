import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx

from services.behavior_engine import analyze_trade_psychology
from services.gemini_client import gemini_rotator

logger = logging.getLogger(__name__)

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
    analysis = analyze_trade_psychology(trade_list)

    # Narrative generation via Gemini AI or template fallback
    narrative = None
    active_key = gemini_rotator.get_active_key(task_type="light")
    
    if active_key:
        try:
            prompt = f"""
            Act as a Lead Quantitative Trading Psychologist. Based on these 8 behavioral metrics:
            - Disposition Effect Score: {analysis['disposition_score']}
            - Loss Aversion Ratio: {analysis['loss_aversion_ratio']}
            - Revenge Trading Score: {analysis['revenge_score']}%
            - Overtrading Score: {analysis['overtrading_score']}
            - Position Sizing CV: {analysis['position_sizing_cv']}
            - Win Rate: {analysis['win_rate_pct']}%
            - Expectancy: {analysis['expectancy_pct']}%
            - Flags: {analysis['flags']}

            Write 2 concise, actionable paragraphs of psychological coaching advice to help this trader eliminate cognitive biases and improve capital protection. Return raw text only.
            """
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={active_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            
            with httpx.Client(timeout=5.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        narrative = candidates[0]["content"]["parts"][0]["text"]
                        gemini_rotator.report_success(active_key)
                else:
                    gemini_rotator.report_error(active_key, status_code=res.status_code)
        except Exception as e:
            logger.warning(f"Gemini psychology advice failed ({e}). Using template fallback.")

    if not narrative:
        disp = analysis["disposition_score"]
        la = analysis["loss_aversion_ratio"]
        narrative = (
            f"Your trade analysis indicates a Disposition Effect score of {disp}x and Loss Aversion Ratio of {la}x. "
            f"Holding losing positions significantly longer than winning ones erodes long-term portfolio expectancy. "
            f"Establishing fixed stop-loss orders prior to trade execution will enforce strict risk management discipline."
        )

    return {
        "metrics": analysis,
        "flags": analysis["flags"],
        "narrative": narrative,
        "ai_generated": bool(active_key and narrative)
    }
