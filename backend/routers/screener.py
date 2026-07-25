from fastapi import APIRouter, Query
from typing import Optional
from services.screener_engine import filter_stocks, PRESET_SCREENS, get_sector_heatmap

router = APIRouter(prefix="/api/screener", tags=["screener"])

@router.get("")
def run_screener(
    preset: Optional[str] = None,
    min_pe: Optional[float] = None,
    max_pe: Optional[float] = None,
    min_pb: Optional[float] = None,
    max_pb: Optional[float] = None,
    min_roe: Optional[float] = None,
    min_roce: Optional[float] = None,
    max_debt_equity: Optional[float] = None,
    min_div_yield: Optional[float] = None,
    min_revenue_growth: Optional[float] = None,
    min_eps_growth: Optional[float] = None,
    min_promoter: Optional[float] = None,
    max_pledged: Optional[float] = None,
    sector: Optional[str] = None,
):
    filters = {}

    if preset and preset in PRESET_SCREENS:
        filters = PRESET_SCREENS[preset]["filters"].copy()

    # Manual query params override preset filters
    if min_pe is not None: filters["min_pe"] = min_pe
    if max_pe is not None: filters["max_pe"] = max_pe
    if min_pb is not None: filters["min_pb"] = min_pb
    if max_pb is not None: filters["max_pb"] = max_pb
    if min_roe is not None: filters["min_roe"] = min_roe
    if min_roce is not None: filters["min_roce"] = min_roce
    if max_debt_equity is not None: filters["max_debt_equity"] = max_debt_equity
    if min_div_yield is not None: filters["min_div_yield"] = min_div_yield
    if min_revenue_growth is not None: filters["min_revenue_growth"] = min_revenue_growth
    if min_eps_growth is not None: filters["min_eps_growth"] = min_eps_growth
    if min_promoter is not None: filters["min_promoter"] = min_promoter
    if max_pledged is not None: filters["max_pledged"] = max_pledged
    if sector is not None: filters["sector"] = sector

    results = filter_stocks(filters)
    return {
        "count": len(results),
        "preset_applied": preset,
        "filters_applied": filters,
        "results": results
    }

@router.get("/presets")
def get_preset_screens():
    return {"presets": PRESET_SCREENS}

@router.get("/sector-heatmap")
def get_heatmap():
    heatmap = get_sector_heatmap()
    return {"heatmap": heatmap}
