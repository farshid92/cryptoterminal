import numpy as np

from features.builder import build_feature_frame
from features.registry import FEATURE_LIST
from features.technical import compute_all


def test_registry_is_explicit_and_compute_all_matches_it(fake_candles):
    result = compute_all(fake_candles)

    assert result.columns.tolist() == ["time", *FEATURE_LIST]
    assert len(FEATURE_LIST) >= 40
    assert result["time"].is_monotonic_increasing


def test_technical_features_are_causal(fake_candles):
    baseline = compute_all(fake_candles)
    changed = fake_candles.copy()
    changed.loc[100:, "close"] = 10_000
    changed.loc[100:, "high"] = 10_001
    changed_features = compute_all(changed)

    np.testing.assert_allclose(
        baseline.loc[:99, FEATURE_LIST].to_numpy(),
        changed_features.loc[:99, FEATURE_LIST].to_numpy(),
        equal_nan=True,
    )


def test_builder_preserves_symbol_and_time(fake_candles):
    source = fake_candles.assign(symbol="BTCUSDT")

    result = build_feature_frame(source)

    assert result.columns.tolist() == ["symbol", "time", *FEATURE_LIST]
    assert result["symbol"].eq("BTCUSDT").all()
