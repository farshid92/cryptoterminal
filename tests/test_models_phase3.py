"""Focused tests for P3 baselines and XGBoost wrapper."""

import numpy as np
import pandas as pd

from models.baselines import baseline_metrics, buy_hold, random_strategy, rsi_reversal, sma_cross
from models.xgb_model import XGBoostModel


def test_baselines_are_deterministic_and_signal_only():
    frame = pd.DataFrame({"close": [100.0, 101.0, 99.0, 102.0, 103.0]})

    assert len(buy_hold(frame)) == len(frame)
    pd.testing.assert_series_equal(random_strategy(frame), random_strategy(frame))
    assert len(rsi_reversal(frame, period=2)) == len(frame)
    assert len(sma_cross(frame, fast=2, slow=3)) == len(frame)
    assert set(baseline_metrics(frame)) == {"buyhold", "random", "rsi_reversal", "sma_cross"}


def test_xgboost_wrapper_returns_three_class_probabilities():
    X = pd.DataFrame({"f1": np.arange(30), "f2": np.arange(30) % 3})
    y = pd.Series(np.tile([-1, 0, 1], 10))

    model = XGBoostModel(n_estimators=5, max_depth=2).fit(X, y)
    probabilities = model.predict_proba(X.iloc[:4])

    assert probabilities.shape == (4, 3)
    assert list(probabilities.columns) == [-1, 0, 1]
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0)
