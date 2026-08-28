import pandas as pd
import pytest

from labeling.triple_barrier import triple_barrier
from labeling.sample_weights import sample_weights
from backtest.purged_cv import purged_cv
from labeling.validation import class_distribution, split_last_months


def test_triple_barrier_assigns_first_touch_and_return():
    candles = pd.DataFrame({"close": [100.0, 101.0, 104.0, 98.0, 100.0]})

    result = triple_barrier(candles, atr=2.0, horizon=3, tp_m=2.0, sl_m=1.0)

    assert result.loc[0, "label"] == 1
    assert result.loc[0, "touch_i"] == 2
    assert result.loc[0, "ret"] == pytest.approx(0.04)
    assert result.loc[1, "label"] == -1
    assert result.loc[1, "touch_i"] == 3


def test_triple_barrier_expires_neutral_at_horizon():
    candles = pd.DataFrame({"close": [100.0, 100.5, 100.2, 100.4]})

    result = triple_barrier(candles, atr=10.0, horizon=2)

    assert result["label"].tolist() == [0, 0, 0, 0]
    assert result["touch_i"].tolist() == [2, 3, 3, 3]


def test_sample_weights_are_positive_and_normalized():
    labels = pd.DataFrame({"label": [1, 0, -1], "ret": [0.1, 0.0, -0.2]})

    weights = sample_weights(labels, touch_times=[2, 2, 2], time_decay=0.5)

    assert (weights > 0).all()
    assert weights.mean() == pytest.approx(1.0)


def test_purged_cv_has_no_overlapping_training_events():
    touch_times = [3, 4, 5, 6, 7, 8, 9, 9, 9, 9]

    splits = purged_cv(10, touch_times, n_splits=2, embargo_bars=1)

    for train, test in splits:
        test_start, test_stop = min(test), max(test)
        assert not set(train).intersection(test)
        assert all(touch_times[index] < test_start or index > test_stop + 1 for index in train)


def test_class_distribution_includes_all_required_classes():
    distribution = class_distribution(pd.Series([-1, 0, 1, 1]))

    assert distribution.index.tolist() == [-1, 0, 1]
    assert distribution.sum() == pytest.approx(1.0)


def test_last_month_holdout_is_chronologically_untouched():
    times = pd.date_range("2024-01-01", periods=400, freq="D", tz="UTC")
    frame = pd.DataFrame({"time": times.view("int64") // 1_000_000, "value": range(400)})

    train, holdout = split_last_months(frame, months=6)

    assert train["time"].max() < holdout["time"].min()
    assert len(holdout) >= 180
