import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes default technical indicators for charting and backtesting.
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

    # RSI 14 (Wilder's Exponential Smoothing)
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0.0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, adjust=False).mean()
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

    # ADX 14 (Average Directional Index)
    df["ADX_14"] = compute_adx(df, period=14)

    # Volume SMA 20 & Volume Spike Flag
    df["VOL_SMA_20"] = df["volume"].rolling(window=20, min_periods=1).mean().round(0)
    df["VOL_SPIKE"] = (df["volume"] > 2.0 * df["VOL_SMA_20"])

    return df

# Alias for backward compatibility
compute_indicators_df = compute_indicators

def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Computes ADX (Average Directional Index) using Wilder's smoothing.
    """
    try:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        tr_smooth = pd.Series(tr).ewm(alpha=1/period, adjust=False).mean()
        plus_di = 100 * (pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean() / (tr_smooth + 1e-10))
        minus_di = 100 * (pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean() / (tr_smooth + 1e-10))

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(alpha=1/period, adjust=False).mean().round(2)
        return adx
    except Exception:
        return pd.Series(25.0, index=df.index)

def compute_custom_indicator(df: pd.DataFrame, indicator: str, params: Dict[str, Any]) -> pd.DataFrame:
    """
    Computes custom indicator series on demand for arbitrary user parameters.
    """
    df = df.copy()
    ind = indicator.upper()

    if ind == "RSI":
        period = int(params.get("period", 14))
        col_name = f"RSI_{period}"
        if col_name not in df.columns:
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0.0)).ewm(alpha=1/period, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/period, adjust=False).mean()
            rs = gain / (loss + 1e-10)
            df[col_name] = (100 - (100 / (1 + rs))).round(2)

    elif ind in ["SMA", "SMA_CROSS"]:
        for key in ["period", "fast_period", "slow_period"]:
            if key in params:
                p = int(params[key])
                col_name = f"SMA_{p}"
                if col_name not in df.columns:
                    df[col_name] = df["close"].rolling(window=p, min_periods=1).mean().round(2)

    elif ind in ["EMA", "EMA_CROSS"]:
        for key in ["period", "fast_period", "slow_period"]:
            if key in params:
                p = int(params[key])
                col_name = f"EMA_{p}"
                if col_name not in df.columns:
                    df[col_name] = df["close"].ewm(span=p, adjust=False).mean().round(2)

    elif ind == "BOLLINGER":
        period = int(params.get("period", 20))
        std_dev = float(params.get("std_dev", 2.0))
        bbu_col = f"BBU_{period}_{std_dev}"
        bbl_col = f"BBL_{period}_{std_dev}"
        if bbu_col not in df.columns:
            sma = df["close"].rolling(window=period, min_periods=1).mean()
            std = df["close"].rolling(window=period, min_periods=1).std().fillna(0)
            df[bbu_col] = (sma + std_dev * std).round(2)
            df[bbl_col] = (sma - std_dev * std).round(2)

    elif ind == "ADX":
        period = int(params.get("period", 14))
        col_name = f"ADX_{period}"
        if col_name not in df.columns:
            df[col_name] = compute_adx(df, period=period)

    return df
