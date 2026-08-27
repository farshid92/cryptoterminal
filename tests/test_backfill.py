from unittest.mock import patch

import pandas as pd

from ingestion.backfill import backfill_ohlcv, save_parquet


def _batch(start_time: int):
    return [
        {
            'symbol': 'BTCUSDT',
            'time': start_time,
            'open': 100.0,
            'high': 101.0,
            'low': 99.5,
            'close': 100.5,
            'volume': 1000.0,
        },
        {
            'symbol': 'BTCUSDT',
            'time': start_time + 60_000,
            'open': 100.5,
            'high': 101.5,
            'low': 100.0,
            'close': 101.0,
            'volume': 1100.0,
        },
    ]


def test_backfill_ohlcv_iterates_and_normalizes_multiple_pages():
    calls = []

    def side_effect(symbol, interval, start, end):
        calls.append((symbol, interval, start, end))
        if start == 0:
            return _batch(0)
        if start == 120_000:
            return _batch(120_000)
        return []

    with patch('ingestion.backfill.fetch_klines', side_effect=side_effect):
        frame = backfill_ohlcv('BTCUSDT', '1m', start_ms=0, end_ms=300_000)

    assert len(calls) == 3
    assert list(frame['time']) == [0, 60_000, 120_000, 180_000]
    assert frame.iloc[-1]['close'] == 101.0


def test_backfill_ohlcv_can_limit_batches_for_smoke_runs():
    calls = []

    def side_effect(symbol, interval, start, end):
        calls.append((symbol, interval, start, end))
        return _batch(0)

    with patch('ingestion.backfill.fetch_klines', side_effect=side_effect):
        frame = backfill_ohlcv('BTCUSDT', '1m', start_ms=0, end_ms=300_000, max_batches=1)

    assert len(calls) == 1
    assert list(frame['time']) == [0, 60_000]


def test_save_parquet_writes_output(tmp_path, monkeypatch):
    frame = pd.DataFrame({'symbol': ['BTCUSDT'], 'time': [0], 'open': [1.0], 'high': [1.1], 'low': [0.9], 'close': [1.0], 'volume': [10.0]})
    output = tmp_path / 'backfill.parquet'

    called = {}

    def fake_to_parquet(self, path, **kwargs):
        called['path'] = path
        called['index'] = kwargs.get('index')

    monkeypatch.setattr(pd.DataFrame, 'to_parquet', fake_to_parquet)
    path = save_parquet(frame, output)

    assert path == output
    assert called['path'] == output
    assert called['index'] is False
