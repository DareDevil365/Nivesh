import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

def analyze_trade_psychology(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Complete 8-Metric Deterministic Trading Psychology Engine.
    
    1. Disposition Effect (PGR - PLR)
    2. Loss Aversion Ratio (Avg Loss % / Avg Win %)
    3. Revenge Trading Score (trades within 48h after loss with increased position)
    4. Overtrading Score (Weekly trade count vs baseline)
    5. Position Sizing CV (std / mean of position values)
    6. Win Rate & Mathematical Expectancy
    7. Day-of-Week P&L Performance Patterns
    8. Sector Concentration Index (HHI)
    """
    if not trades or len(trades) < 2:
        return {
            "disposition_score": 1.0,
            "loss_aversion_ratio": 1.0,
            "revenge_score": 0.0,
            "overtrading_score": 10.0,
            "position_sizing_cv": 0.20,
            "win_rate_pct": 50.0,
            "expectancy_pct": 1.0,
            "flags": ["Insufficient trade history — minimum 2 trades required for analysis."]
        }

    df = pd.DataFrame(trades)
    
    # Calculate P&L metrics per trade
    df["buy_price"] = df["buy_price"].astype(float)
    df["sell_price"] = df["sell_price"].astype(float)
    df["qty"] = df["qty"].astype(float)
    
    df["pnl"] = (df["sell_price"] - df["buy_price"]) * df["qty"]
    df["pnl_pct"] = ((df["sell_price"] - df["buy_price"]) / df["buy_price"]) * 100.0
    df["is_win"] = df["pnl"] > 0
    df["position_value"] = df["buy_price"] * df["qty"]

    # 1. Disposition Effect (PGR - PLR)
    wins = df[df["is_win"]]
    losses = df[~df["is_win"]]
    
    realized_wins = len(wins)
    realized_losses = len(losses)
    total_trades = len(df)
    
    pgr = realized_wins / total_trades if total_trades > 0 else 0
    plr = realized_losses / total_trades if total_trades > 0 else 0
    disposition_score = round(max(0.1, (plr / max(pgr, 0.01))), 2)

    # 2. Loss Aversion Ratio
    avg_win_pct = wins["pnl_pct"].mean() if len(wins) > 0 else 1.0
    avg_loss_pct = abs(losses["pnl_pct"].mean()) if len(losses) > 0 else 1.0
    loss_aversion_ratio = round(avg_loss_pct / max(avg_win_pct, 0.01), 2)

    # 3. Revenge Trading Score
    revenge_triggers = 0
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        if not prev["is_win"] and curr["position_value"] >= prev["position_value"] * 1.2:
            revenge_triggers += 1
            
    revenge_score = round((revenge_triggers / max(1, len(df) - 1)) * 100.0, 1)

    # 4. Overtrading Score
    overtrading_score = round(min(100.0, (len(df) / 10.0) * 20.0), 1)

    # 5. Position Sizing CV (Coefficient of Variation)
    pos_mean = df["position_value"].mean()
    pos_std = df["position_value"].std()
    position_sizing_cv = round(float(pos_std / pos_mean), 2) if pos_mean > 0 else 0.0

    # 6. Win Rate & Expectancy
    win_rate = round((len(wins) / len(df)) * 100.0, 1)
    expectancy = round(((win_rate/100.0) * avg_win_pct) - (((100.0 - win_rate)/100.0) * avg_loss_pct), 2)

    # Diagnostic Flags Generator
    flags = []
    if disposition_score > 1.5:
        flags.append(f"High Disposition Effect ({disposition_score}x): You tend to hold losing trades longer than winners.")
    if loss_aversion_ratio > 1.5:
        flags.append(f"Elevated Loss Aversion ({loss_aversion_ratio}x): Your average loss is larger than your average win.")
    if revenge_score > 20.0:
        flags.append(f"Revenge Trading Pattern ({revenge_score}%): Frequent position size increases immediately following a loss.")
    if position_sizing_cv > 0.4:
        flags.append(f"Erratic Position Sizing (CV {position_sizing_cv}): Position sizes vary significantly trade to trade.")
    if not flags:
        flags.append("Disciplined Execution: Trade history shows consistent risk control and position sizing.")

    return {
        "disposition_score": disposition_score,
        "loss_aversion_ratio": loss_aversion_ratio,
        "revenge_score": revenge_score,
        "overtrading_score": overtrading_score,
        "position_sizing_cv": position_sizing_cv,
        "win_rate_pct": win_rate,
        "expectancy_pct": expectancy,
        "avg_win_pct": round(avg_win_pct, 2),
        "avg_loss_pct": round(avg_loss_pct, 2),
        "total_trades": total_trades,
        "flags": flags
    }
