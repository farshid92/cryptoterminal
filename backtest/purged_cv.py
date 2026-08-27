"""Purge-aware cross-validation utilities."""

from __future__ import annotations

def purged_cv(n, touch_times, n_splits=5, embargo_bars=0):
    """Yield purged train/test index splits.

    Args:
        n: total number of rows.
        touch_times: iterable of event end indices aligned to rows.
        n_splits: number of sequential folds.
        embargo_bars: number of rows to embargo after each test window.

    Returns:
        List of (train_indices, test_indices) tuples.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if n_splits <= 0:
        raise ValueError("n_splits must be positive")
    if embargo_bars < 0:
        raise ValueError("embargo_bars must be non-negative")

    touch_list = list(touch_times)
    if touch_list and len(touch_list) != n:
        raise ValueError("touch_times must match n when provided")

    fold_sizes = [n // n_splits] * n_splits
    for index in range(n % n_splits):
        fold_sizes[index] += 1

    splits = []
    start = 0
    for fold_size in fold_sizes:
        stop = start + fold_size
        test_indices = list(range(start, stop))
        embargo_stop = min(n, stop + embargo_bars)
        train_indices = []
        for idx in range(n):
            if idx in test_indices:
                continue
            if touch_list and touch_list[idx] >= start and idx < embargo_stop:
                continue
            train_indices.append(idx)

        splits.append((train_indices, test_indices))
        start = stop

    return splits
