"""Causal derived features built from OHLCV and technical features."""

from __future__ import annotations

import pandas as pd


def compute_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Compute causal crosses, slopes, and market regime features."""
    if df is None:
        raise TypeError("df must be a pandas DataFrame")
    required = {"time", "close", "volume"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"missing required columns: {', '.join(sorted(missing))}")

    frame = df.sort_values("time").reset_index(drop=True)
    close = frame["close"].astype(float)
    volume = frame["volume"].astype(float)
    sma_10 = close.rolling(10, min_periods=10).mean()
    sma_20 = close.rolling(20, min_periods=20).mean()
    ema_12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema_26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    rsi = 100 - 100 / (
        1
        + close.diff().clip(lower=0).rolling(14, min_periods=14).mean()
        / (-close.diff().clip(upper=0).rolling(14, min_periods=14).mean())
    )
    volatility = close.pct_change().rolling(20, min_periods=20).std(ddof=0)
    volume_mean = volume.rolling(20, min_periods=20).mean()

    result = pd.DataFrame(
        {
            "time": frame["time"].astype("int64"),
            "sma_10_20_cross": (sma_10 - sma_20).where(sma_10.notna() & sma_20.notna()),
            "ema_12_26_cross": (ema_12 - ema_26).where(ema_12.notna() & ema_26.notna()),
            "rsi_slope_5": rsi.diff(5),
            "close_slope_20": close.pct_change(20),
            "trend_regime": (sma_10 > sma_20).astype("int8").where(sma_20.notna()),
            "volatility_regime": (volatility > volatility.rolling(100, min_periods=100).median())
            .astype("int8")
            .where(volatility.notna()),
            "volume_regime": (volume > volume_mean).astype("int8").where(volume_mean.notna()),
        }
    )
    return result
