"""Tests for P3 walk-forward training pipeline."""

import numpy as np
import pandas as pd
import pytest

from features.registry import FEATURE_LIST
from models.training_pipeline import (
    evaluate_baselines_wf,
    evaluate_model_wf,
    p3_gate_check,
    prepare_training_frame,
)


def test_prepare_training_frame_validates_required_columns(tmp_path):
    artifact = pd.DataFrame({
        "label": [-1, 0, 1],
        "weight": [1.0, 1.0, 1.0],
        **{f: [0.0] * 3 for f in FEATURE_LIST},
    })
    artifact_path = tmp_path / "artifact.parquet"
    artifact.to_parquet(artifact_path, index=False)

    result = prepare_training_frame(artifact_path)

    assert len(result) == 3
    assert {"label", "weight"}.issubset(result.columns)


def test_prepare_training_frame_aligns_features_by_timestamp(tmp_path):
    artifact = pd.DataFrame({
        "symbol": ["BTCUSDT", "BTCUSDT"],
        "time": [2, 4],
        "label": [-1, 1],
        "ret": [-0.01, 0.02],
        "weight": [1.0, 1.0],
    })
    source = pd.DataFrame({
        "symbol": ["BTCUSDT"] * 4,
        "time": [1, 2, 3, 4],
        "open": [100.0] * 4,
        "high": [101.0] * 4,
        "low": [99.0] * 4,
        "close": [100.0, 101.0, 100.0, 102.0],
        "volume": [1.0] * 4,
    })
    artifact_path = tmp_path / "artifact.parquet"
    source_path = tmp_path / "source.parquet"
    artifact.to_parquet(artifact_path, index=False)
    source.to_parquet(source_path, index=False)

    result = prepare_training_frame(artifact_path, source_path=source_path)

    assert result["time"].tolist() == [2, 4]
    assert set(FEATURE_LIST).issubset(result.columns)


def test_evaluate_baselines_wf_requires_ohlcv():
    n_rows = 200
    artifact = pd.DataFrame({
        "label": np.tile([-1, 0, 1], n_rows // 3 + 1)[:n_rows],
        "weight": [1.0] * n_rows,
        "close": np.linspace(100, 105, n_rows),
        "high": np.linspace(101, 106, n_rows),
        "low": np.linspace(99, 104, n_rows),
        "volume": [1000.0] * n_rows,
        **{f: [0.0] * n_rows for f in FEATURE_LIST},
    })

    results = evaluate_baselines_wf(artifact)

    assert isinstance(results, dict)
    assert set(results.keys()) == {"buyhold", "random", "rsi_reversal", "sma_cross"}
    for baseline_name, metrics in results.items():
        assert "sharpe" in metrics
        assert "max_drawdown" in metrics
        assert "profit_factor" in metrics
        assert "signal_coverage" in metrics


def test_evaluate_model_wf_produces_gate_metrics():
    n_rows = 1000
    artifact = pd.DataFrame({
        "label": np.tile([-1, 0, 1], n_rows // 3 + 1)[:n_rows],
        "weight": [1.0] * n_rows,
        "ret": np.random.randn(n_rows) * 0.01,
        "close": np.linspace(100, 105, n_rows),
        "high": np.linspace(101, 106, n_rows),
        "low": np.linspace(99, 104, n_rows),
        **{f: np.random.randn(n_rows) for f in FEATURE_LIST},
    })

    results = evaluate_model_wf(artifact, n_splits=1, seed=42)

    assert "sharpe" in results
    assert "max_drawdown" in results
    assert "profit_factor" in results
    assert "signal_coverage" in results
    assert "rolling90d_positive_sharpe_fraction" in results


def test_p3_gate_check_returns_all_criteria():
    model_metrics = {
        "sharpe": 1.5,
        "max_drawdown": 0.25,
        "profit_factor": 1.5,
        "signal_coverage": 0.15,
    }
    baseline_metrics = {
        "sma_cross": {"sharpe": 1.0, "max_drawdown": 0.5, "profit_factor": 1.0, "signal_coverage": 0.1}
    }

    gates = p3_gate_check(model_metrics, baseline_metrics)

    assert "sharpe_vs_baseline" in gates
    assert "max_drawdown" in gates
    assert "profit_factor" in gates
    assert "signal_coverage" in gates
    assert "rolling90d_sharpe" in gates
    assert all(isinstance(v, bool) for v in gates.values())
