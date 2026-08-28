"""Validation helpers for P2 label gates."""

from __future__ import annotations

import pandas as pd


def class_distribution(labels: pd.Series | pd.DataFrame) -> pd.Series:
    """Return label proportions for the required classes -1, 0, and 1."""
    series = labels["label"] if isinstance(labels, pd.DataFrame) else labels
    if series.empty:
        return pd.Series({-1: 0.0, 0: 0.0, 1: 0.0}, dtype=float)
    counts = series.value_counts(normalize=True).reindex([-1, 0, 1], fill_value=0.0)
    return counts.astype(float)


def split_last_months(frame: pd.DataFrame, months: int = 6) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split chronologically, reserving the final calendar months as untouched holdout."""
    if months < 1:
        raise ValueError("months must be positive")
    if frame is None or frame.empty or "time" not in frame.columns:
        raise ValueError("frame must contain non-empty time-indexed data")
    ordered = frame.sort_values("time").reset_index(drop=True)
    timestamps = pd.to_datetime(ordered["time"], unit="ms", utc=True)
    cutoff = timestamps.max() - pd.DateOffset(months=months)
    train = ordered[timestamps < cutoff].reset_index(drop=True)
    holdout = ordered[timestamps >= cutoff].reset_index(drop=True)
    if train.empty or holdout.empty:
        raise ValueError("frame does not span the requested holdout period")
    return train, holdout
