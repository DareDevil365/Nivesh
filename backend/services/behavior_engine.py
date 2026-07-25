import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def analyze_trade_behavior(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes pure statistical trading psychology metrics.
    Zero LLM required for numeric math.
    """
    if not trades or len(trades) < 2:
        return {
            "disposition_effect_score": 1.0,
            "loss_aversion_ratio": 1.0,
            "revenge_trading_score": 0.0,
            "overtrading_score": 25.0,
            "position_sizing_cv": 0.20,
            "expectancy_pct": 1.5,
            "win_rate_pct": 50.0,
            "total_trades": len(trades),
            "flags": ["Insufficient trade history — minimum 3 trades recommended"]
        }

    df = pd.DataFrame(trades)
    df["buy_date"] = pd.to_datetime(df["buy_date"])
    df["sell_date"] = pd.to_datetime(df["sell_date"])
    df["holding_days"] = (df["sell_date"] - df["buy_date"]).dt.days.clip(lower=1)
    df["pnl_pct"] = ((df["sell_price"] - df["buy_price"]) / df["buy_price"]) * 100.0
    df["position_value"] = df["buy_price"] * df["qty"]

    winners = df[df["pnl_pct"] > 0]
    losers = df[df["pnl_pct"] < 0]

    # 1. Disposition Effect (Ratio of avg holding days of losers vs winners)
    avg_win_holding = float(winners["holding_days"].mean()) if not winners.empty else 1.0
    avg_loss_holding = float(losers["holding_days"].mean()) if not losers.empty else 1.0
    disposition_score = round(avg_loss_holding / max(1.0, avg_win_holding), 2)

    # 2. Loss Aversion Ratio (avg loss size vs avg win size)
    avg_win_pct = abs(float(winners["pnl_pct"].mean())) if not winners.empty else 1.0
    avg_loss_pct = abs(float(losers["pnl_pct"].mean())) if not losers.empty else 1.0
    loss_aversion_ratio = round(avg_loss_pct / max(0.1, avg_win_pct), 2)

    # 3. Revenge Trading Indicator (Trades opened within 48h of a losing trade exit)
    revenge_trades = 0
    df = df.sort_values("buy_date").reset_index(drop=True)
    for i in range(1, len(df)):
        prev_trade = df.iloc[i-1]
        curr_trade = df.iloc[i]
        if prev_trade["pnl_pct"] < 0:
            time_gap_hrs = (curr_trade["buy_date"] - prev_trade["sell_date"]).total_seconds() / 3600.0
            if 0 <= time_gap_hrs <= 48:
                if curr_trade["position_value"] >= prev_trade["position_value"] * 0.9:
                    revenge_trades += 1

    revenge_score = round((revenge_trades / max(1, len(df))) * 100.0, 1)

    # 4. Position Sizing Consistency (Coefficient of variation: std / mean)
    sizes = df["position_value"].values
    mean_size = np.mean(sizes) if len(sizes) > 0 else 1.0
    std_size = np.std(sizes) if len(sizes) > 0 else 0.0
    position_sizing_cv = round(float(std_size / max(1.0, mean_size)), 2)

    # 5. Expectancy & Win Rate
    win_rate = round(len(winners) / len(df) * 100.0, 1)
    loss_rate = 100.0 - win_rate
    expectancy = round(((win_rate/100.0) * avg_win_pct) - ((loss_rate/100.0) * avg_loss_pct), 2)

    # Rule-Based Behavioral Flags
    flags = []
    if disposition_score > 2.0:
        flags.append(f"Disposition Effect Detected: You hold losing positions {disposition_score}x longer than winners.")
    if loss_aversion_ratio > 1.5:
        flags.append(f"High Loss Aversion: Your average loss ({avg_loss_pct:.1f}%) is substantially larger than your average gain ({avg_win_pct:.1f}%).")
    if revenge_score > 20.0:
        flags.append(f"Revenge Trading Alert: {revenge_score}% of your trades were opened quickly after a loss with large position size.")
    if position_sizing_cv > 0.40:
        flags.append(f"Erratic Position Sizing: High variation (CV = {position_sizing_cv}) across bet sizes.")

    if not flags:
        flags.append("Disciplined Execution: Balanced holding periods and consistent risk management observed.")

    return {
        "metrics": {
            "disposition_effect_score": disposition_score,
            "loss_aversion_ratio": loss_aversion_ratio,
            "revenge_trading_score": revenge_score,
            "position_sizing_cv": position_sizing_cv,
            "win_rate_pct": win_rate,
            "expectancy_pct": expectancy,
            "avg_win_holding_days": round(avg_win_holding, 1),
            "avg_loss_holding_days": round(avg_loss_holding, 1),
            "total_trades": len(df)
        },
        "flags": flags
    }
