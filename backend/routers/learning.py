"""Deterministic, hypothetical exercises; never inferred company forecasts."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/learn", tags=["learning"])


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    revenue: float = Field(gt=0, le=1e9)
    growth_pct: float = Field(ge=-100, le=200)
    margin_pct: float = Field(ge=-100, le=100)
    shares: float = Field(ge=0.000001, le=1e9)
    dilution_pct: float = Field(ge=0, le=200)
    pe: float = Field(gt=0, le=200)
    current_price: float = Field(ge=0.000001, le=1e9)


@router.post("/scenario")
def scenario(data: Scenario):
    revenue = data.revenue * (1 + data.growth_pct / 100)
    profit = revenue * data.margin_pct / 100
    shares = data.shares * (1 + data.dilution_pct / 100)
    eps = profit / shares
    price = eps * data.pe if eps > 0 else None
    return {
        "revenue": revenue,
        "profit": profit,
        "shares": shares,
        "eps": eps,
        "scenario_price": price,
        "price_change_pct": (price / data.current_price - 1) * 100 if price is not None else None,
        "status": "illustration" if price is not None else "pe_not_applicable",
        "assumptions": "One-period hypothetical non-financial business. Revenue and shares must use matching scales (e.g. rupees crore and shares crore). Net margin incorporates assumed costs, tax and financing; share count is simplified, not accounting weighted-average diluted EPS. P/E is an assumption, not a predicted market multiple. Excludes dividends, timing, cash/debt bridge and transaction costs; not suitable for banks or insurers. No live data or AI is used.",
    }
