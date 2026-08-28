"""Deterministic, signal-only baseline strategies."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest.metrics import strategy_metrics


def _close(frame: pd.DataFrame) -> pd.Series:
    if frame is None or "close" not in frame.columns:
        raise KeyError("frame must include close")
    return frame["close"].astype(float).reset_index(drop=True)


def buy_hold(frame: pd.DataFrame) -> pd.Series:
    """Return one-period buy-and-hold returns."""
    close = _close(frame)
    return close.pct_change().fillna(0.0)


def random_strategy(frame: pd.DataFrame, seed: int = 42) -> pd.Series:
    """Return deterministic random long/short exposure returns."""
    close_returns = buy_hold(frame)
    rng = np.random.default_rng(seed)
    exposure = pd.Series(rng.choice([-1.0, 1.0], size=len(close_returns)))
    return close_returns * exposure


def rsi_reversal(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    """Return returns from a causal RSI reversal signal."""
    if period < 1:
        raise ValueError("period must be positive")
    close_returns = buy_hold(frame)
    delta = _close(frame).diff()
    gains = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    losses = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gains / losses.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    signal = pd.Series(np.where(rsi < 30.0, 1.0, np.where(rsi > 70.0, -1.0, 0.0)))
    return close_returns * signal.shift(1).fillna(0.0)


def sma_cross(frame: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    """Return returns from a causal fast/slow SMA crossover signal."""
    if fast < 1 or slow <= fast:
        raise ValueError("slow must be greater than fast and both must be positive")
    close = _close(frame)
    close_returns = close.pct_change().fillna(0.0)
    fast_sma = close.rolling(fast, min_periods=fast).mean()
    slow_sma = close.rolling(slow, min_periods=slow).mean()
    signal = pd.Series(np.where(fast_sma > slow_sma, 1.0, -1.0))
    return close_returns * signal.shift(1).fillna(0.0)


def baseline_metrics(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Evaluate all required baselines and return their gate metrics."""
    strategies = {
        "buyhold": buy_hold(frame),
        "random": random_strategy(frame),
        "rsi_reversal": rsi_reversal(frame),
        "sma_cross": sma_cross(frame),
    }
    return {
        name: strategy_metrics(returns.tolist(), (returns != 0.0).astype(float).tolist())
        for name, returns in strategies.items()
    }
