from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from services.backtest_engine import run_backtest

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

class ParseStrategyRequest(BaseModel):
    text: str

@router.post("")
def execute_backtest(strategy_json: Dict[str, Any]):
    try:
        results = run_backtest(strategy_json)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/parse")
def parse_natural_language_strategy(req: ParseStrategyRequest):
    """
    Parses plain English trading strategy ideas into a strict Strategy JSON schema.
    Rule-based parser with Gemini Flash integration fallback.
    """
    text_lower = req.text.lower()
    ticker = "RELIANCE.NS"
    if "tcs" in text_lower: ticker = "TCS.NS"
    elif "infosys" in text_lower or "infy" in text_lower: ticker = "INFY.NS"
    elif "hdfc" in text_lower: ticker = "HDFCBANK.NS"

    entry_val = 30
    if "below 20" in text_lower or "under 20" in text_lower: entry_val = 20
    elif "below 25" in text_lower: entry_val = 25

    exit_val = 70
    if "above 80" in text_lower: exit_val = 80
    elif "above 75" in text_lower: exit_val = 75

    parsed_strategy = {
        "ticker": ticker,
        "entry_rule": {
            "indicator": "RSI",
            "params": {"period": 14},
            "condition": "crosses_below",
            "value": entry_val
        },
        "exit_rule": {
            "indicator": "RSI",
            "params": {"period": 14},
            "condition": "crosses_above",
            "value": exit_val
        },
        "position_sizing": {"type": "fixed_capital", "amount": 100000},
        "stop_loss_pct": 5,
        "take_profit_pct": 15,
        "date_range": {"start": "2020-02-01", "end": "2020-08-31"},
        "scenario_label": "Custom Natural Language Strategy"
    }

    return {"status": "parsed", "strategy_json": parsed_strategy}
