"""Local Feast repository setup and online latency measurement."""

from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from feast import Entity, FeatureService, FeatureStore, FeatureView, Field, FileSource
from feast.types import Float32
from feast.value_type import ValueType

from features.registry import FEATURE_LIST


def prepare_feast_repo(source_frame: pd.DataFrame, repo_path: str | Path) -> FeatureStore:
    """Create and apply a local SQLite-backed Feast repository."""
    if source_frame is None or source_frame.empty:
        raise ValueError("source_frame must contain feature rows")
    missing = {"symbol", "time", *FEATURE_LIST}.difference(source_frame.columns)
    if missing:
        raise KeyError(f"missing feature columns: {', '.join(sorted(missing))}")

    root = Path(repo_path)
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    source_path = data_dir / "features.parquet"
    frame = source_frame[["symbol", "time", *FEATURE_LIST]].copy()
    frame["event_timestamp"] = pd.to_datetime(frame["time"], unit="ms", utc=True)
    frame.to_parquet(source_path, index=False)
    (root / "feature_store.yaml").write_text(
        "project: cryptoterminal\n"
        "provider: local\n"
        "registry: data/registry.db\n"
        "online_store:\n"
        "  type: sqlite\n"
        "  path: data/online_store.db\n",
        encoding="utf-8",
    )

    entity = Entity(name="symbol", join_keys=["symbol"], value_type=ValueType.STRING)
    source = FileSource(
        path=str(source_path),
        event_timestamp_column="event_timestamp",
    )
    schema = [Field(name=name, dtype=Float32) for name in FEATURE_LIST]
    view = FeatureView(
        name="btc_features",
        entities=[entity],
        schema=schema,
        source=source,
        online=True,
    )
    service = FeatureService(name="btc_feature_service", features=[view])
    store = FeatureStore(repo_path=str(root))
    store.apply([entity, source, view, service])
    return store


def materialize_and_benchmark(
    store: FeatureStore,
    end_time: datetime,
    iterations: int = 100,
) -> dict[str, float | int]:
    """Materialize local features and return online retrieval latency statistics."""
    if iterations < 1:
        raise ValueError("iterations must be positive")
    store.materialize_incremental(end_time)
    entity_rows = [{"symbol": "BTCUSDT"}]
    features = [f"btc_features:{name}" for name in FEATURE_LIST]
    samples_ms: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        store.get_online_features(features=features, entity_rows=entity_rows)
        samples_ms.append((time.perf_counter_ns() - started) / 1_000_000)
    ordered = sorted(samples_ms)
    p99_index = min(len(ordered) - 1, int(len(ordered) * 0.99))
    return {
        "iterations": iterations,
        "p50_ms": statistics.median(ordered),
        "p99_ms": ordered[p99_index],
        "max_ms": max(ordered),
    }


def benchmark_frame(source_frame: pd.DataFrame, repo_path: str | Path, iterations: int = 100) -> dict[str, float | int]:
    """Prepare, materialize, and benchmark a local Feast repository."""
    store = prepare_feast_repo(source_frame, repo_path)
    end_time = datetime.now(timezone.utc)
    return materialize_and_benchmark(store, end_time, iterations=iterations)
