from backtest.metrics import sharpe_ratio
from backtest.purged_cv import purged_cv


def test_purged_cv_creates_purged_train_test_splits():
    splits = purged_cv(10, touch_times=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], n_splits=5, embargo_bars=1)

    assert len(splits) == 5
    first_train, first_test = splits[0]
    assert first_test == [0, 1]
    assert 0 not in first_train
    assert 1 not in first_train
    assert 2 not in first_train


def test_sharpe_ratio_returns_zero_for_flat_series():
    assert sharpe_ratio([0.01, 0.01, 0.01]) == 0.0


def test_sharpe_ratio_is_positive_for_positive_mean_returns():
    value = sharpe_ratio([0.01, 0.02, 0.03, 0.01])

    assert value > 0
