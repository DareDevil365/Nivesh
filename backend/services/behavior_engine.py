"""Descriptive closed-trade statistics; pattern flags are heuristics, not diagnoses."""

from datetime import date
from statistics import mean, stdev

from services.trade_parser import Trade


def analyze_trade_psychology(trades):
    rows = [Trade.model_validate(t).model_dump(mode="json") for t in trades]
    for t in rows:
        t["pnl"] = (t["sell_price"] - t["buy_price"]) * t["qty"] - t["costs"]
        t["pnl_pct"] = t["pnl"] / (t["buy_price"] * t["qty"]) * 100
        t["position"] = t["buy_price"] * t["qty"]
        t["holding_days"] = (
            date.fromisoformat(t["sell_date"]) - date.fromisoformat(t["buy_date"])
        ).days
    if len(rows) < 2:
        return {
            "total_trades": len(rows),
            "insufficient_data": True,
            "disposition_score": None,
            "loss_aversion_ratio": None,
            "revenge_score": None,
            "overtrading_score": None,
            "position_sizing_cv": None,
            "win_rate_pct": None,
            "expectancy_pct": None,
            "flags": [
                "At least two valid closed observations are required. A larger sample is needed for stable conclusions."
            ],
        }
    wins = [t for t in rows if t["pnl"] > 0]
    losses = [t for t in rows if t["pnl"] < 0]
    avg_win = mean(t["pnl_pct"] for t in wins) if wins else None
    avg_loss = -mean(t["pnl_pct"] for t in losses) if losses else None
    win_days = mean(t["holding_days"] for t in wins) if wins else None
    loss_days = mean(t["holding_days"] for t in losses) if losses else None
    holding_ratio = round(loss_days / win_days, 2) if loss_days is not None and win_days else None
    events = []
    for i, t in enumerate(rows):
        events.extend(
            [
                (date.fromisoformat(t["buy_date"]), 1, i),
                (date.fromisoformat(t["sell_date"]), 0, i),
            ]
        )
    last_loss, flags_count = None, 0
    for date_value, event, i in sorted(events):
        t = rows[i]
        if event == 0 and t["pnl"] < 0:
            last_loss = (date_value, i)
        elif event == 1 and last_loss is not None and last_loss[1] != i:
            if (
                0 <= (date_value - last_loss[0]).days <= 2
                and t["position"] >= rows[last_loss[1]]["position"] * 1.2
            ):
                flags_count += 1
    start = min(date.fromisoformat(t["buy_date"]) for t in rows)
    end = max(date.fromisoformat(t["sell_date"]) for t in rows)
    weeks = max(1, (end - start).days / 7)
    sizes = [t["position"] for t in rows]
    flags = []
    if len(rows) < 30:
        flags.append(
            "Small sample: fewer than 30 matched observations. Treat patterns as exploratory."
        )
    if holding_ratio is not None and holding_ratio > 1.5:
        flags.append(
            "Losing observations were held longer on average than winners. This does not establish a disposition effect without unrealized position data."
        )
    if flags_count:
        flags.append(
            f"{flags_count} entries increased size by at least 20% within two calendar days of a realized loss. Date-only exports cannot establish intraday order or motivation."
        )
    flags.append(
        "Closed trades cannot measure unrealized gains/losses or diagnose loss aversion. Frequency alone does not establish overtrading."
    )
    return {
        "total_trades": len(rows),
        "insufficient_data": False,
        "disposition_score": holding_ratio,
        "loss_aversion_ratio": round(avg_loss / avg_win, 2)
        if avg_loss is not None and avg_win
        else None,
        "revenge_score": round(flags_count / len(rows) * 100, 2),
        "overtrading_score": None,
        "position_sizing_cv": round(stdev(sizes) / mean(sizes), 2),
        "win_rate_pct": round(len(wins) / len(rows) * 100, 2),
        "expectancy_pct": round(mean(t["pnl_pct"] for t in rows), 2),
        "avg_win_pct": round(avg_win, 2) if avg_win is not None else None,
        "avg_loss_pct": round(avg_loss, 2) if avg_loss is not None else None,
        "avg_winner_holding_days": win_days,
        "avg_loser_holding_days": loss_days,
        "trades_per_week": round(len(rows) / weeks, 2),
        "total_pnl": round(sum(t["pnl"] for t in rows), 2),
        "total_costs": round(sum(t["costs"] for t in rows), 2),
        "flags": flags,
    }
