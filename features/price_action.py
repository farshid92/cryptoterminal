"""Causal price-action pattern and structure detectors."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd


def _frame(c: pd.DataFrame | Sequence[Mapping[str, float]]) -> pd.DataFrame:
    frame = c.copy() if isinstance(c, pd.DataFrame) else pd.DataFrame(c)
    required = {"open", "high", "low", "close"}
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"missing required columns: {', '.join(sorted(missing))}")
    return frame.sort_values("time").reset_index(drop=True) if "time" in frame else frame.reset_index(drop=True)


def detect_patterns(c: pd.DataFrame | Sequence[Mapping[str, float]]) -> list[dict[str, float | str]]:
    """Detect patterns on the latest candle using only data available through it."""
    frame = _frame(c)
    if frame.empty:
        return []
    row = frame.iloc[-1]
    candle_range = float(row["high"] - row["low"])
    if candle_range <= 0:
        return []
    body = abs(float(row["close"] - row["open"]))
    upper_wick = float(row["high"] - max(row["open"], row["close"]))
    lower_wick = float(min(row["open"], row["close"]) - row["low"])
    patterns: list[dict[str, float | str]] = []
    if body / candle_range <= 0.1:
        patterns.append({"name": "doji", "bias": "neutral", "strength": 1.0})
    if lower_wick >= body * 2 and lower_wick >= upper_wick * 1.5:
        patterns.append({"name": "hammer", "bias": "long", "strength": min(1.0, lower_wick / candle_range)})
    if upper_wick >= body * 2 and upper_wick >= lower_wick * 1.5:
        patterns.append({"name": "shooting_star", "bias": "short", "strength": min(1.0, upper_wick / candle_range)})
    return patterns


def support_resistance(
    c: pd.DataFrame | Sequence[Mapping[str, float]],
    n_swing: int = 20,
    cluster_pct: float = 0.005,
) -> list[dict[str, float | str]]:
    """Return clustered recent swing support and resistance levels."""
    if n_swing < 1 or cluster_pct < 0:
        raise ValueError("n_swing must be positive and cluster_pct non-negative")
    frame = _frame(c)
    if frame.empty:
        return []
    window = frame.tail(n_swing)
    close = float(frame.iloc[-1]["close"])
    levels: list[dict[str, float | str]] = []
    for price, level_type in (
        (float(window["low"].min()), "support"),
        (float(window["high"].max()), "resistance"),
    ):
        if close and abs(price - close) / abs(close) <= cluster_pct:
            level_type = "support" if price <= close else "resistance"
        levels.append({"price": price, "type": level_type, "dist_pct": (price / close - 1) * 100})
    return levels
