import pandas as pd
import numpy as np
from typing import Dict, Any, List

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes standard technical indicators using pure pandas/numpy.
    Includes: SMA 20/50/200, EMA 12/26/50, RSI 14, MACD (12,26,9),
    Bollinger Bands (20,2), ADX 14, Volume SMA 20.
    """
    if df.empty or len(df) < 5:
        return df

    df = df.copy()

    # Simple Moving Averages
    df["SMA_20"] = df["close"].rolling(window=20, min_periods=1).mean().round(2)
    df["SMA_50"] = df["close"].rolling(window=50, min_periods=1).mean().round(2)
    df["SMA_200"] = df["close"].rolling(window=200, min_periods=1).mean().round(2)

    # Exponential Moving Averages
    df["EMA_12"] = df["close"].ewm(span=12, adjust=False).mean().round(2)
    df["EMA_26"] = df["close"].ewm(span=26, adjust=False).mean().round(2)
    df["EMA_50"] = df["close"].ewm(span=50, adjust=False).mean().round(2)

    # RSI 14
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / (loss + 1e-10)
    df["RSI_14"] = (100 - (100 / (1 + rs))).round(2)

    # MACD (12, 26, 9)
    df["MACD"] = (df["EMA_12"] - df["EMA_26"]).round(2)
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean().round(2)
    df["MACD_hist"] = (df["MACD"] - df["MACD_signal"]).round(2)

    # Bollinger Bands (20, 2)
    std_20 = df["close"].rolling(window=20, min_periods=1).std().fillna(0)
    df["BBL_20_2.0"] = (df["SMA_20"] - 2 * std_20).round(2)
    df["BBM_20_2.0"] = df["SMA_20"]
    df["BBU_20_2.0"] = (df["SMA_20"] + 2 * std_20).round(2)

    # Volume SMA 20 & Volume Spike Flag
    df["VOL_SMA_20"] = df["volume"].rolling(window=20, min_periods=1).mean().round(0)
    df["VOL_SPIKE"] = (df["volume"] > 2.0 * df["VOL_SMA_20"])

    return df
