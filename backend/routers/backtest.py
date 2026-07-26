import re
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import httpx

from services.backtest_engine import run_backtest
from services.nse_stock_master import NSE_MASTER_LIST
from services.gemini_client import gemini_rotator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

class ParseStrategyRequest(BaseModel):
    text: str

@router.post("")
def execute_backtest(strategy_json: Dict[str, Any]):
    try:
        results = run_backtest(
            ticker=strategy_json.get("ticker", "RELIANCE.NS"),
            entry_rule=strategy_json.get("entry_rule", {"indicator": "RSI", "condition": "crosses_below", "value": 30}),
            exit_rule=strategy_json.get("exit_rule", {"indicator": "RSI", "condition": "crosses_above", "value": 70}),
            initial_capital=float(strategy_json.get("position_sizing", {}).get("amount", 100000.0)),
            stop_loss_pct=float(strategy_json.get("stop_loss_pct", 5.0)),
            take_profit_pct=float(strategy_json.get("take_profit_pct", 15.0)) if strategy_json.get("take_profit_pct") else None,
            start_date=strategy_json.get("date_range", {}).get("start"),
            end_date=strategy_json.get("date_range", {}).get("end")
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/parse")
def parse_natural_language_strategy(req: ParseStrategyRequest):
    """
    Parses plain English trading strategy ideas into strict Strategy JSON schemas.
    Attempts Gemini Flash JSON-schema parsing first, with automatic fallback to
    rule-based regex parser if AI is unavailable or rate limited.
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty prompt provided.")

    # Attempt Gemini LLM structured parsing if key is available
    active_key = gemini_rotator.get_active_key(task_type="heavy")
    if active_key:
        try:
            prompt = f"""
            Parse the following trading strategy into a JSON object strictly matching this schema:
            {{
                "ticker": "NSE symbol with .NS suffix e.g. RELIANCE.NS, TCS.NS",
                "entry_rule": {{
                    "indicator": "RSI | SMA_CROSS | EMA_CROSS | MACD | BOLLINGER",
                    "params": {{"period": 14}},
                    "condition": "crosses_below | crosses_above | touches_lower",
                    "value": 30
                }},
                "exit_rule": {{
                    "indicator": "RSI | SMA_CROSS | EMA_CROSS | MACD | BOLLINGER",
                    "params": {{"period": 14}},
                    "condition": "crosses_above | crosses_below | touches_upper",
                    "value": 70
                }},
                "position_sizing": {{"type": "fixed_capital", "amount": 100000}},
                "stop_loss_pct": 5.0,
                "take_profit_pct": 15.0,
                "date_range": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}},
                "scenario_label": "Short description of period"
            }}

            Strategy Prompt: "{text}"
            Return ONLY the valid JSON object.
            """
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={active_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            
            with httpx.Client(timeout=6.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        json_str = candidates[0]["content"]["parts"][0]["text"]
                        parsed_json = json.loads(json_str)
                        gemini_rotator.report_success(active_key)
                        return {"status": "parsed", "source": "gemini_ai", "strategy_json": parsed_json}
                else:
                    gemini_rotator.report_error(active_key, status_code=res.status_code)
        except Exception as e:
            logger.warning(f"Gemini API parse failed ({e}). Falling back to rule-based parser.")
            gemini_rotator.report_error(active_key, status_code=500)

    # ---------------------------------------------------------
    # FALLBACK: Enhanced Rule-Based Parser (0 LLM reliance)
    # ---------------------------------------------------------
    text_lower = text.lower()
    ticker = "RELIANCE.NS"

    # Extract Ticker
    for symbol_key, meta in NSE_MASTER_LIST.items():
        clean_sym = symbol_key.replace(".NS", "").lower()
        if clean_sym in text_lower or meta["name"].lower() in text_lower:
            ticker = symbol_key
            break

    ticker_match = re.search(r'\b([a-zA-Z0-9\-]+)\.ns\b', text_lower)
    if ticker_match:
        ticker = f"{ticker_match.group(1).upper()}.NS"

    # Scenario Detection
    start_date = "2020-02-01"
    end_date = "2020-08-31"
    scenario_label = "Custom Backtest"

    if "harshad" in text_lower or "1992" in text_lower or "scam" in text_lower:
        start_date = "1992-03-01"
        end_date = "1992-06-30"
        scenario_label = "Harshad Mehta Scam (SENSEX Index Approx)"
    elif "ketan" in text_lower or "2000" in text_lower or "dotcom" in text_lower:
        start_date = "2000-02-01"
        end_date = "2001-09-30"
        scenario_label = "Ketan Parekh Dot-Com Crash"
    elif "gfc" in text_lower or "2008" in text_lower or "crisis" in text_lower:
        start_date = "2008-01-01"
        end_date = "2009-03-31"
        scenario_label = "Global Financial Crisis"
    elif "demonetization" in text_lower or "2016" in text_lower:
        start_date = "2016-11-01"
        end_date = "2017-01-31"
        scenario_label = "2016 Demonetization"
    elif "covid" in text_lower or "2020" in text_lower:
        start_date = "2020-02-01"
        end_date = "2020-08-31"
        scenario_label = "COVID-19 Crash & Recovery"
    elif "adani" in text_lower or "hindenburg" in text_lower or "2023" in text_lower:
        start_date = "2023-01-15"
        end_date = "2023-04-30"
        scenario_label = "Adani-Hindenburg Episode"

    # Indicator Rules
    entry_indicator = "RSI"
    entry_condition = "crosses_below"
    entry_val = 30.0
    entry_params = {"period": 14}

    exit_indicator = "RSI"
    exit_condition = "crosses_above"
    exit_val = 70.0
    exit_params = {"period": 14}

    if "golden cross" in text_lower or ("sma" in text_lower and "cross" in text_lower):
        entry_indicator = "SMA_CROSS"
        entry_condition = "crosses_above"
        entry_params = {"fast_period": 20, "slow_period": 50}
        exit_indicator = "SMA_CROSS"
        exit_condition = "crosses_below"
        exit_params = {"fast_period": 20, "slow_period": 50}
    elif "macd" in text_lower:
        entry_indicator = "MACD"
        entry_condition = "crosses_above"
        exit_indicator = "MACD"
        exit_condition = "crosses_below"
    elif "rsi" in text_lower:
        nums = [float(n) for n in re.findall(r'\b\d+\.?\d*\b', text) if float(n) <= 100]
        if len(nums) >= 2:
            entry_val = min(nums)
            exit_val = max(nums)
        elif len(nums) == 1:
            entry_val = nums[0]

    # Risk Controls
    stop_loss_pct = 5.0
    take_profit_pct = 15.0
    sl_match = re.search(r'(?:stop\s*loss|sl)\s*(?:of|at|=|\:)?\s*(\d+(?:\.\d+)?)%?', text_lower)
    if sl_match:
        stop_loss_pct = float(sl_match.group(1))

    tp_match = re.search(r'(?:take\s*profit|target|tp)\s*(?:of|at|=|\:)?\s*(\d+(?:\.\d+)?)%?', text_lower)
    if tp_match:
        take_profit_pct = float(tp_match.group(1))

    parsed_strategy = {
        "ticker": ticker,
        "entry_rule": {
            "indicator": entry_indicator,
            "params": entry_params,
            "condition": entry_condition,
            "value": entry_val
        },
        "exit_rule": {
            "indicator": exit_indicator,
            "params": exit_params,
            "condition": exit_condition,
            "value": exit_val
        },
        "position_sizing": {"type": "fixed_capital", "amount": 100000},
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct,
        "date_range": {"start": start_date, "end": end_date},
        "scenario_label": f"{scenario_label} ({ticker.replace('.NS','')})"
    }

    return {"status": "parsed", "source": "rule_based", "strategy_json": parsed_strategy}
