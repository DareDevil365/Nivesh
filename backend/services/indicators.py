"""Indicators require a complete warm-up window; no partial-window signals."""

import numpy as np
import pandas as pd


def compute_custom_indicator(df, indicator, params):
    df = df.copy()
    close = df["close"].astype(float)
    period = int(params.get("period", 14))
    if indicator == "RSI":
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
        rsi = rsi.mask((loss == 0) & (gain > 0), 100).mask((loss == 0) & (gain == 0), 50)
        df[f"RSI_{period}"] = rsi
    elif indicator in {"SMA", "SMA_CROSS", "EMA", "EMA_CROSS"}:
        for p in {int(params[k]) for k in ("period", "fast_period", "slow_period") if k in params}:
            name = "EMA" if indicator.startswith("EMA") else "SMA"
            df[f"{name}_{p}"] = (
                close.ewm(span=p, adjust=False, min_periods=p).mean()
                if name == "EMA"
                else close.rolling(p, min_periods=p).mean()
            )
    elif indicator == "MACD":
        fast, slow, signal = (
            int(params.get(k, v))
            for k, v in (("fast_period", 12), ("slow_period", 26), ("signal_period", 9))
        )
        df["MACD"] = (
            close.ewm(span=fast, adjust=False, min_periods=fast).mean()
            - close.ewm(span=slow, adjust=False, min_periods=slow).mean()
        )
        df["MACD_signal"] = df["MACD"].ewm(span=signal, adjust=False, min_periods=signal).mean()
        df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    elif indicator == "BOLLINGER":
        p, std = int(params.get("period", 20)), float(params.get("std_dev", 2))
        mean, deviation = close.rolling(p).mean(), close.rolling(p).std(ddof=0)
        df[f"BBL_{p}_{std}"] = mean - std * deviation
        df[f"BBU_{p}_{std}"] = mean + std * deviation
    return df


def compute_adx(df, period=14):
    up = df["high"].diff()
    down = -df["low"].diff()
    plus = up.where((up > down) & (up > 0), 0)
    minus = down.where((down > up) & (down > 0), 0)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    pdi = (
        100
        * plus.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        / atr.replace(0, np.nan)
    )
    mdi = (
        100
        * minus.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        / atr.replace(0, np.nan)
    )
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def compute_indicators(df):
    df = df.copy()
    for p in (20, 50, 200):
        df = compute_custom_indicator(df, "SMA", {"period": p})
    for p in (12, 20, 26, 50, 200):
        df = compute_custom_indicator(df, "EMA", {"period": p})
    df = compute_custom_indicator(df, "RSI", {"period": 14})
    df = compute_custom_indicator(df, "MACD", {})
    df = compute_custom_indicator(df, "BOLLINGER", {"period": 20, "std_dev": 2.0})
    df["ADX_14"] = compute_adx(df)
    df["VOL_SMA_20"] = df["volume"].rolling(20).mean()
    df["VOL_SPIKE"] = df["volume"] > 2 * df["VOL_SMA_20"]
    return df


compute_indicators_df = compute_indicators
