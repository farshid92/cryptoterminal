"""Feature building and parquet materialization."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from features.technical import compute_all


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Merge source identifiers with causal technical features."""
    if df is None:
        raise TypeError("df must be a pandas DataFrame")
    features = compute_all(df)
    identifiers = [column for column in ("symbol", "time") if column in df.columns]
    if "time" not in identifiers:
        raise KeyError("df must include time")
    result = features
    if "symbol" in identifiers:
        result = df[["symbol", "time"]].sort_values("time").reset_index(drop=True).copy()
        result = result.join(features.drop(columns="time"))
    return result


def save_feature_frame(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Write a feature frame to parquet and return its path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path
