"""Triple-barrier labeling logic."""

from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit


@njit(cache=True)
def _label_arrays(
    closes: np.ndarray,
    atr_values: np.ndarray,
    horizon: int,
    tp_m: float,
    sl_m: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    labels = np.zeros(len(closes), dtype=np.int8)
    touch_indices = np.full(len(closes), -1, dtype=np.int64)
    returns = np.zeros(len(closes), dtype=np.float64)
    for index in range(len(closes)):
        entry = closes[index]
        end = min(len(closes) - 1, index + horizon)
        upper = entry + tp_m * atr_values[index]
        lower = entry - sl_m * atr_values[index]
        touch = end
        label = 0
        for future_index in range(index + 1, end + 1):
            price = closes[future_index]
            if price >= upper:
                label, touch = 1, future_index
                break
            if price <= lower:
                label, touch = -1, future_index
                break
        labels[index] = label
        touch_indices[index] = touch
        returns[index] = closes[touch] / entry - 1
    return labels, touch_indices, returns


def triple_barrier(
    c: pd.DataFrame,
    atr: pd.Series | np.ndarray | float,
    horizon: int,
    tp_m: float = 2.0,
    sl_m: float = 1.0,
) -> pd.DataFrame:
    """Assign first-touch labels, touch indices, and returns to each close."""
    if c is None or "close" not in c.columns:
        raise KeyError("c must include a close column")
    if horizon < 1:
        raise ValueError("horizon must be positive")
    if tp_m <= 0 or sl_m <= 0:
        raise ValueError("tp_m and sl_m must be positive")
    closes = c["close"].astype(float).reset_index(drop=True)
    atr_values = np.broadcast_to(np.asarray(atr, dtype=float), (len(closes),))
    if len(atr_values) != len(closes):
        raise ValueError("atr must align with c")
    labels, touch_indices, returns = _label_arrays(
        closes.to_numpy(),
        np.asarray(atr_values, dtype=float),
        horizon,
        tp_m,
        sl_m,
    )

    return pd.DataFrame({"label": labels, "touch_i": touch_indices, "ret": returns})
