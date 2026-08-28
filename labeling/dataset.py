"""Leakage-safe labeled dataset construction."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from labeling.sample_weights import sample_weights
from labeling.triple_barrier import triple_barrier
from labeling.validation import (
    BALANCED_LABELING_CONFIG,
    assert_holdout_excluded,
    balance_labeled_frame,
    split_last_months,
)


def build_training_artifact(
    frame: pd.DataFrame,
    output_path: str | Path,
    holdout_months: int = 6,
    atr_window: int = 14,
    config: dict[str, float | int] | None = None,
    balance_classes: bool = True,
    seed: int = 42,
) -> tuple[Path, pd.DataFrame]:
    """Build and persist labels using only rows before the untouched holdout."""
    if atr_window < 1:
        raise ValueError("atr_window must be positive")
    required = {"time", "high", "low", "close"}
    if frame is None or not required.issubset(frame.columns):
        raise KeyError(f"frame must include: {', '.join(sorted(required))}")
    train, holdout = split_last_months(frame, months=holdout_months)
    assert_holdout_excluded(train, holdout)
    true_range = pd.concat(
        [
            train["high"] - train["low"],
            (train["high"] - train["close"].shift()).abs(),
            (train["low"] - train["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = true_range.rolling(atr_window, min_periods=atr_window).mean().bfill()
    labeling_config = config or BALANCED_LABELING_CONFIG
    labels = triple_barrier(
        train[["close"]],
        atr,
        horizon=int(labeling_config["horizon"]),
        tp_m=float(labeling_config["tp_m"]),
        sl_m=float(labeling_config["sl_m"]),
    )
    labels["weight"] = sample_weights(
        labels,
        touch_times=labels["touch_i"],
    ).to_numpy()
    artifact = train.reset_index(drop=True).copy()
    artifact[["label", "touch_i", "ret", "weight"]] = labels
    if balance_classes and set(artifact["label"].astype(int).unique()) == {-1, 0, 1}:
        artifact = balance_labeled_frame(artifact, seed=seed)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    artifact.to_parquet(output, index=False)
    assert_holdout_excluded(artifact, holdout)
    return output, artifact
