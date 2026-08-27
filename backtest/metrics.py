"""Performance metrics for strategy evaluation."""

from __future__ import annotations

import math


def sharpe_ratio(returns):
    """Compute the annualized Sharpe ratio for a return series."""
    values = [float(value) for value in returns]
    if not values:
        raise ValueError("returns must not be empty")

    mean_return = sum(values) / len(values)
    variance = sum((value - mean_return) ** 2 for value in values) / len(values)
    if variance == 0:
        return 0.0

    return (mean_return / math.sqrt(variance)) * math.sqrt(252.0)
