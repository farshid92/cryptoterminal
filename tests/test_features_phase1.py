import numpy as np

from features.builder import build_feature_frame
from features.registry import FEATURE_LIST, TECHNICAL_FEATURES
from features.technical import compute_all
from features.derived import compute_derived


def test_registry_is_explicit_and_compute_all_matches_it(fake_candles):
    result = compute_all(fake_candles)

    assert result.columns.tolist() == ["time", *TECHNICAL_FEATURES]
    assert len(FEATURE_LIST) == 50
    assert result["time"].is_monotonic_increasing


def test_technical_features_are_causal(fake_candles):
    baseline = compute_all(fake_candles)
    changed = fake_candles.copy()
    changed.loc[100:, "close"] = 10_000
    changed.loc[100:, "high"] = 10_001
    changed_features = compute_all(changed)

    np.testing.assert_allclose(
        baseline.loc[:99, TECHNICAL_FEATURES].to_numpy(),
        changed_features.loc[:99, TECHNICAL_FEATURES].to_numpy(),
        equal_nan=True,
    )


def test_builder_preserves_symbol_and_time(fake_candles):
    source = fake_candles.assign(symbol="BTCUSDT")

    result = build_feature_frame(source)

    assert result.columns.tolist() == ["symbol", "time", *FEATURE_LIST]
    assert result["symbol"].eq("BTCUSDT").all()


def test_derived_features_are_causal(fake_candles):
    baseline = compute_derived(fake_candles)
    changed = fake_candles.copy()
    changed.loc[100:, "close"] = 10_000
    changed_features = compute_derived(changed)

    np.testing.assert_allclose(
        baseline.loc[:99].to_numpy(),
        changed_features.loc[:99].to_numpy(),
        equal_nan=True,
    )
