"""Pure technical feature calculations for OHLCV frames."""

from __future__ import annotations

import numpy as np
import pandas as pd

from features.registry import FEATURE_LIST


def _require_columns(frame: pd.DataFrame) -> None:
    missing = {"open", "high", "low", "close", "volume", "time"}.difference(frame.columns)
    if missing:
        raise KeyError(f"missing required columns: {', '.join(sorted(missing))}")


def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
    x = np.arange(window, dtype=float)
    x_centered = x - x.mean()
    denominator = float(np.dot(x_centered, x_centered))

    def slope(values: np.ndarray) -> float:
        y = values - values.mean()
        return float(np.dot(x_centered, y) / denominator)

    return series.rolling(window, min_periods=window).apply(slope, raw=True)


def compute_all(df_ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Compute deterministic, causal technical features from OHLCV data."""
    if df_ohlcv is None:
        raise TypeError("df_ohlcv must be a pandas DataFrame")
    _require_columns(df_ohlcv)
    if df_ohlcv.empty:
        return pd.DataFrame(columns=["time", *FEATURE_LIST], index=df_ohlcv.index)

    frame = df_ohlcv.sort_values("time").reset_index(drop=True).copy()
    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    volume = frame["volume"].astype(float)
    returns = close.pct_change()
    true_range = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    direction = np.sign(close.diff()).fillna(0.0)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    atr = true_range.rolling(14, min_periods=14).mean()
    plus_di = 100 * plus_dm.rolling(14, min_periods=14).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.rolling(14, min_periods=14).mean() / atr.replace(0, np.nan)
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).replace(
        [np.inf, -np.inf], np.nan
    )
    volume_sma = volume.rolling(20, min_periods=20).mean()
    bb_mid = close.rolling(20, min_periods=20).mean()
    bb_std = close.rolling(20, min_periods=20).std(ddof=0)
    rolling_std = close.rolling(20, min_periods=20).std(ddof=0)
    result = pd.DataFrame(
        {
            "time": frame["time"].astype("int64"),
            "return_1": returns,
            "return_3": close.pct_change(3),
            "return_6": close.pct_change(6),
            "return_12": close.pct_change(12),
            "return_24": close.pct_change(24),
            "sma_10": close.rolling(10, min_periods=10).mean(),
            "sma_20": close.rolling(20, min_periods=20).mean(),
            "sma_50": close.rolling(50, min_periods=50).mean(),
            "ema_12": close.ewm(span=12, adjust=False, min_periods=12).mean(),
            "ema_26": close.ewm(span=26, adjust=False, min_periods=26).mean(),
            "ema_50": close.ewm(span=50, adjust=False, min_periods=50).mean(),
            "ema_200": close.ewm(span=200, adjust=False, min_periods=200).mean(),
            "macd": close.ewm(span=12, adjust=False, min_periods=12).mean()
            - close.ewm(span=26, adjust=False, min_periods=26).mean(),
            "rsi_14": 100
            - 100
            / (
                1
                + close.diff().clip(lower=0).rolling(14, min_periods=14).mean()
                / (-close.diff().clip(upper=0).rolling(14, min_periods=14).mean())
            ),
            "stoch_k": 100 * (close - low.rolling(14, min_periods=14).min())
            / (high.rolling(14, min_periods=14).max() - low.rolling(14, min_periods=14).min()),
            "bb_mid": bb_mid,
            "bb_upper": bb_mid + 2 * bb_std,
            "bb_lower": bb_mid - 2 * bb_std,
            "bb_width": (4 * bb_std / bb_mid.replace(0, np.nan)),
            "atr_14": atr,
            "true_range": true_range,
            "adx_14": dx.rolling(14, min_periods=14).mean(),
            "plus_di_14": plus_di,
            "minus_di_14": minus_di,
            "obv": (direction * volume).cumsum(),
            "volume_sma_20": volume_sma,
            "volume_ratio": volume / volume_sma.replace(0, np.nan),
            "vwap": (close * volume).cumsum() / volume.cumsum().replace(0, np.nan),
            "hl_range": (high - low) / close.replace(0, np.nan),
            "oc_change": (close - frame["open"]) / frame["open"].replace(0, np.nan),
            "body_ratio": (close - frame["open"]).abs() / (high - low).replace(0, np.nan),
            "upper_wick_ratio": (high - pd.concat([frame["open"], close], axis=1).max(axis=1))
            / (high - low).replace(0, np.nan),
            "lower_wick_ratio": (pd.concat([frame["open"], close], axis=1).min(axis=1) - low)
            / (high - low).replace(0, np.nan),
            "rolling_high_20": high.rolling(20, min_periods=20).max(),
            "rolling_low_20": low.rolling(20, min_periods=20).min(),
            "distance_high_20": close / high.rolling(20, min_periods=20).max() - 1,
            "distance_low_20": close / low.rolling(20, min_periods=20).min() - 1,
            "close_zscore_20": (close - bb_mid) / rolling_std.replace(0, np.nan),
            "volatility_20": returns.rolling(20, min_periods=20).std(ddof=0),
            "trend_slope_20": _rolling_slope(close, 20),
        }
    )
    result["macd_signal"] = result["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    result["macd_hist"] = result["macd"] - result["macd_signal"]
    result["stoch_d"] = result["stoch_k"].rolling(3, min_periods=3).mean()
    return result[["time", *FEATURE_LIST]]
