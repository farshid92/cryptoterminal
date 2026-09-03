"""Performance metrics for strategy evaluation."""

from __future__ import annotations

import math
from collections.abc import Sequence


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


def max_drawdown(returns: Sequence[float]) -> float:
    """Return the maximum peak-to-trough loss for periodic strategy returns."""
    equity = 1.0
    peak = equity
    drawdown = 0.0
    for value in returns:
        equity *= 1.0 + float(value)
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1.0)
    return abs(drawdown)


def profit_factor(returns: Sequence[float]) -> float:
    """Return gross profits divided by gross losses, or infinity with no losses."""
    gains = sum(max(float(value), 0.0) for value in returns)
    losses = sum(-min(float(value), 0.0) for value in returns)
    if losses == 0.0:
        return math.inf if gains > 0.0 else 0.0
    return gains / losses


def signal_coverage(signals: Sequence[float]) -> float:
    """Return the fraction of predictions that are not neutral."""
    values = [float(value) for value in signals]
    if not values:
        raise ValueError("signals must not be empty")
    return sum(value != 0.0 for value in values) / len(values)


def rolling_positive_sharpe_fraction(
    returns: Sequence[float],
    window: int = 129_600,
) -> float:
    """Return the fraction of complete 90-day (1-minute) windows with positive Sharpe."""
    if window < 1:
        raise ValueError("window must be positive")
    values = [float(value) for value in returns]
    if len(values) < window:
        return 0.0
    windows = len(values) - window + 1
    positive = sum(sharpe_ratio(values[index : index + window]) > 0.0 for index in range(windows))
    return positive / windows


def strategy_metrics(returns: Sequence[float], signals: Sequence[float]) -> dict[str, float]:
    """Return the P3 strategy gate metrics for aligned returns and signals."""
    if len(returns) != len(signals):
        raise ValueError("returns and signals must have equal lengths")
    if not returns:
        raise ValueError("returns must not be empty")
    return {
        "sharpe": sharpe_ratio(returns),
        "max_drawdown": max_drawdown(returns),
        "profit_factor": profit_factor(returns),
        "signal_coverage": signal_coverage(signals),
    }
