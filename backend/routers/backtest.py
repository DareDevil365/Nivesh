import re
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from schemas import Strategy
from services.backtest_engine import run_backtest
from services.data_fetcher import normalize_ticker
from services.nse_stock_master import NSE_MASTER_LIST

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class ParseStrategyRequest(BaseModel):
    text: str = Field(min_length=5, max_length=2000)


@router.post("")
def execute_backtest(strategy: Strategy):
    try:
        return run_backtest(
            ticker=strategy.ticker,
            entry_rule=strategy.entry_rule.model_dump(),
            exit_rule=strategy.exit_rule.model_dump(),
            initial_capital=strategy.position_sizing.amount,
            stop_loss_pct=strategy.stop_loss_pct,
            take_profit_pct=strategy.take_profit_pct,
            start_date=strategy.date_range.start.isoformat(),
            end_date=strategy.date_range.end.isoformat(),
            cost_bps=strategy.cost_bps,
            slippage_bps=strategy.slippage_bps,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/parse")
def parse_natural_language_strategy(req: ParseStrategyRequest):
    text = req.text.lower().strip()
    if any(word in text for word in ("short sell", "shorting", "options", "futures", "intraday")):
        raise HTTPException(
            422,
            "This engine supports long-only daily stock strategies. Use a supported strategy.",
        )
    ticker = None
    explicit = re.search(r"\b([a-z0-9&.-]+\.(?:ns|bo))\b", text)
    if explicit:
        ticker = normalize_ticker(explicit.group(1))
    else:
        for symbol, meta in sorted(NSE_MASTER_LIST.items(), key=lambda item: -len(item[0])):
            clean = symbol.replace(".NS", "").lower()
            if (
                re.search(r"(?<![a-z0-9])" + re.escape(clean) + r"(?![a-z0-9])", text)
                or meta["name"].lower() in text
            ):
                ticker = symbol
                break
    if ticker is None:
        raise HTTPException(422, "Include an NSE/BSE symbol, for example RELIANCE.NS.")
    if len(set(re.findall(r"\b(?:rsi|macd|sma|ema|bollinger)\b", text))) > 1:
        raise HTTPException(
            422,
            "The text parser supports one indicator. Configure different entry/exit indicators directly in the builder.",
        )
    indicator = next(
        (
            name
            for word, name in [
                ("bollinger", "BOLLINGER"),
                ("macd", "MACD"),
                ("ema", "EMA_CROSS"),
                ("sma", "SMA_CROSS"),
                ("golden cross", "SMA_CROSS"),
                ("rsi", "RSI"),
            ]
            if word in text
        ),
        None,
    )
    if indicator is None:
        raise HTTPException(
            422, "Specify RSI, SMA crossover, EMA crossover, MACD, or Bollinger bands."
        )
    params = {"period": 14}
    entry_value, exit_value = 30, 70
    entry_condition, exit_condition = "crosses_below", "crosses_above"
    if indicator == "RSI":
        entry_match = re.search(
            r"(?:buy|enter|entry).*?(below|under|above|over|<|>)\s*(\d+(?:\.\d+)?)", text
        )
        exit_match = re.search(
            r"(?:sell|exit).*?(below|under|above|over|<|>)\s*(\d+(?:\.\d+)?)", text
        )
        if not entry_match or not exit_match:
            raise HTTPException(
                422,
                "For RSI, specify buy and sell thresholds, e.g. buy below 30 and sell above 70.",
            )
        entry_condition = (
            "crosses_below" if entry_match.group(1) in {"below", "under", "<"} else "crosses_above"
        )
        exit_condition = (
            "crosses_below" if exit_match.group(1) in {"below", "under", "<"} else "crosses_above"
        )
        entry_value, exit_value = float(entry_match.group(2)), float(exit_match.group(2))
        period = re.search(r"rsi\s*\(?\s*(\d+)\s*\)?", text)
        if period:
            params["period"] = int(period.group(1))
    elif indicator == "BOLLINGER":
        params = {"period": 20, "std_dev": 2}
        entry_condition = (
            "touches_upper" if re.search(r"(?:buy|enter|entry).*?upper", text) else "touches_lower"
        )
        exit_condition = (
            "touches_lower" if re.search(r"(?:sell|exit).*?lower", text) else "touches_upper"
        )
    else:
        entry_condition = (
            "crosses_below"
            if re.search(r"(?:buy|enter|entry).*?cross(?:es)?\s+below", text)
            else "crosses_above"
        )
        exit_condition = (
            "crosses_above"
            if re.search(r"(?:sell|exit).*?cross(?:es)?\s+above", text)
            else "crosses_below"
        )
        pair = re.search(
            r"(\d+)\s*(?:/|and|over|above|below|crosses?\s*(?:above|below)?)\s*(\d+)",
            text,
        )
        params = {
            "fast_period": int(pair.group(1)) if pair else 12 if indicator == "MACD" else 20,
            "slow_period": int(pair.group(2)) if pair else 26 if indicator == "MACD" else 50,
            "signal_period": 9,
        }
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
    warnings = [
        "Review all parsed rules before running. Unspecified capital uses ₹100,000; costs use 10 bps and slippage 5 bps per side. This parser supports one indicator and daily long-only bars."
    ]
    if dates and len(dates) != 2:
        raise HTTPException(422, "Provide both start and end dates in YYYY-MM-DD format.")
    date_range = (
        {"start": dates[0], "end": dates[1]}
        if dates
        else {
            "start": (date.today() - timedelta(days=365 * 3)).isoformat(),
            "end": date.today().isoformat(),
        }
    )
    if not dates:
        warnings.append(
            "No explicit dates supplied; using the last three years. Select a historical scenario in the builder if needed."
        )

    def risk(pattern, default):
        match = re.search(pattern, text)
        return float(match.group(1)) if match else default

    payload = {
        "ticker": ticker,
        "entry_rule": {
            "indicator": indicator,
            "condition": entry_condition,
            "value": entry_value,
            "params": params,
        },
        "exit_rule": {
            "indicator": indicator,
            "condition": exit_condition,
            "value": exit_value,
            "params": params,
        },
        "date_range": date_range,
        "stop_loss_pct": risk(r"(?:stop[ -]?loss|sl)\s*(?:at|of|:|=)?\s*(\d+(?:\.\d+)?)", 5),
        "take_profit_pct": risk(
            r"(?:take[ -]?profit|target|tp)\s*(?:at|of|:|=)?\s*(\d+(?:\.\d+)?)", 15
        ),
    }
    try:
        strategy = Strategy.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(422, "; ".join(e["msg"] for e in exc.errors())) from exc
    return {
        "status": "parsed",
        "source": "rule_based",
        "strategy_json": strategy.model_dump(mode="json"),
        "warnings": warnings,
    }
