"""Sample-weighting utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd


def sample_weights(
    labels: pd.DataFrame | pd.Series,
    returns: pd.Series | np.ndarray | None = None,
    touch_times: pd.Series | np.ndarray | None = None,
    time_decay: float = 0.0,
) -> pd.Series:
    """Compute normalized uniqueness, return-magnitude, and time-decay weights."""
    if time_decay < 0:
        raise ValueError("time_decay must be non-negative")
    frame = labels if isinstance(labels, pd.DataFrame) else pd.DataFrame({"label": labels})
    if "label" not in frame:
        raise KeyError("labels must include a label column")
    count = len(frame)
    if count == 0:
        return pd.Series(dtype=float, name="weight")
    returns_array = (
        frame["ret"].to_numpy(dtype=float)
        if returns is None and "ret" in frame
        else np.zeros(count)
        if returns is None
        else np.asarray(returns, dtype=float)
    )
    if len(returns_array) != count:
        raise ValueError("returns must align with labels")
    if touch_times is None:
        touch_array = np.arange(count)
    else:
        touch_array = np.asarray(touch_times, dtype=int)
        if len(touch_array) != count:
            raise ValueError("touch_times must align with labels")
    active_counts = np.ones(count, dtype=float)
    for index, end in enumerate(touch_array):
        if end >= index:
            active_counts[index : min(count, end + 1)] += 1
    uniqueness = 1 / active_counts
    magnitude = np.abs(returns_array) + 1e-12
    magnitude = magnitude / magnitude.mean() if magnitude.mean() > 0 else np.ones(count)
    age = np.arange(count, dtype=float)
    decay = np.exp(-time_decay * (count - 1 - age) / max(count - 1, 1))
    weights = uniqueness * magnitude * decay
    weights = weights / weights.mean() if weights.mean() > 0 else np.ones(count)
    return pd.Series(weights, index=frame.index, name="weight")
