from typing import List, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.behavior_engine import analyze_trade_psychology
from services.trade_parser import Trade, parse_trade_csv

router = APIRouter(prefix="/api/behavior", tags=["behavior"])


class CSVRequest(BaseModel):
    csv_text: str = Field(min_length=10, max_length=2_000_000)
    broker: Literal["auto", "zerodha", "groww", "generic"] = "auto"


class AnalyzeBehaviorRequest(BaseModel):
    trades: List[Trade] = Field(default_factory=list, max_length=20000)


@router.post("/upload")
def upload_trade_csv(req: CSVRequest):
    try:
        return {"status": "parsed", **parse_trade_csv(req.csv_text, req.broker)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/analyze")
def analyze_behavior(req: AnalyzeBehaviorRequest):
    metrics = analyze_trade_psychology([t.model_dump(mode="json") for t in req.trades])
    return {
        "metrics": metrics,
        "flags": metrics["flags"],
        "ai_generated": False,
        "narrative": "Review the matched trade sample, holding periods and position sizes together. These are descriptive statistics and time/size heuristics, not psychological diagnoses. Fees are included only when supplied in the costs column.",
    }
