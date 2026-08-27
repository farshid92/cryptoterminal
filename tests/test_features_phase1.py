import numpy as np

from features.builder import build_feature_frame
from features.registry import FEATURE_LIST, TECHNICAL_FEATURES
from features.technical import compute_all
from features.derived import compute_derived
from features.price_action import detect_patterns, support_resistance


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


def test_price_action_detects_latest_candle_without_future_data():
    candles = [
        {"time": 1, "open": 10.0, "high": 10.2, "low": 9.0, "close": 10.1},
        {"time": 2, "open": 10.1, "high": 10.2, "low": 9.8, "close": 10.0},
    ]

    patterns = detect_patterns(candles)

    assert {pattern["name"] for pattern in patterns} == {"hammer"}
    assert patterns[0]["bias"] == "long"


def test_support_resistance_uses_recent_window():
    candles = [
        {"time": 1, "open": 10, "high": 12, "low": 9, "close": 11},
        {"time": 2, "open": 11, "high": 13, "low": 10, "close": 12},
        {"time": 3, "open": 12, "high": 14, "low": 11, "close": 13},
    ]

    levels = support_resistance(candles, n_swing=2)

    assert levels == [
        {"price": 10.0, "type": "support", "dist_pct": (10 / 13 - 1) * 100},
        {"price": 14.0, "type": "resistance", "dist_pct": (14 / 13 - 1) * 100},
    ]
