"""Feature building and parquet materialization."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from features.derived import compute_derived
from features.registry import FEATURE_LIST
from features.technical import compute_all


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Merge source identifiers with causal technical features."""
    if df is None:
        raise TypeError("df must be a pandas DataFrame")
    features = compute_all(df)
    derived = compute_derived(df)
    identifiers = [column for column in ("symbol", "time") if column in df.columns]
    if "time" not in identifiers:
        raise KeyError("df must include time")
    result = df[identifiers].sort_values("time").reset_index(drop=True).copy()
    result = result.join(features.drop(columns="time"))
    result = result.join(derived.drop(columns="time"))
    return result[identifiers + FEATURE_LIST]


def save_feature_frame(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Write a feature frame to parquet and return its path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def feature_null_rates(frame: pd.DataFrame, warmup: int = 200) -> pd.Series:
    """Return per-feature null rates after the requested warmup period."""
    if warmup < 0:
        raise ValueError("warmup must be non-negative")
    missing = set(FEATURE_LIST).difference(frame.columns)
    if missing:
        raise KeyError(f"missing feature columns: {', '.join(sorted(missing))}")
    return frame.loc[frame.index >= warmup, FEATURE_LIST].isna().mean()


def audit_point_in_time(
    source: pd.DataFrame,
    sample_size: int = 100,
    seed: int = 42,
) -> pd.DataFrame:
    """Recompute a sampled prefix and verify features never use future rows."""
    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    ordered = source.sort_values("time").reset_index(drop=True)
    if ordered.empty:
        return pd.DataFrame(columns=["index", "time", "matched"])
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(len(ordered), size=min(sample_size, len(ordered)), replace=False))
    built = build_feature_frame(ordered)
    prefix_built = build_feature_frame(ordered.iloc[: int(indices[-1]) + 1])
    rows = []
    for index in indices:
        expected = prefix_built.iloc[index][FEATURE_LIST].to_numpy(dtype=float)
        actual = built.iloc[index][FEATURE_LIST].to_numpy(dtype=float)
        rows.append(
            {
                "index": int(index),
                "time": int(ordered.iloc[index]["time"]),
                "matched": bool(np.allclose(expected, actual, equal_nan=True)),
            }
        )
    return pd.DataFrame(rows)
