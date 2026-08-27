import json
from unittest.mock import patch

import pandas as pd

from ingestion.binance_rest import fetch_klines
from ingestion.gap_detector import scan
from ingestion.writers import upsert_candles


class DummyResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        payload = [
            [1700000000000, '100.00', '101.00', '99.50', '100.50', '123.45', '0', '124.00', '9', '0', '0', '0'],
            [1700000060000, '100.50', '102.00', '100.00', '101.25', '150.00', '0', '152.50', '11', '0', '0', '0'],
        ]
        return json.dumps(payload).encode('utf-8')


def test_fetch_klines_parses_binance_payload():
    with patch('ingestion.binance_rest.request.urlopen', return_value=DummyResponse()):
        rows = fetch_klines('BTCUSDT', '1m', 1700000000000, 1700000100000)

    assert len(rows) == 2
    assert rows[0]['symbol'] == 'BTCUSDT'
    assert rows[0]['time'] == 1700000000000
    assert rows[0]['close'] == 100.5
    assert rows[1]['volume'] == 150.0


def test_gap_detector_flags_missing_intervals_without_filling():
    candles = pd.DataFrame(
        {
            'symbol': ['BTCUSDT', 'BTCUSDT', 'BTCUSDT'],
            'time': [0, 60_000, 180_000],
        }
    )

    flagged = scan(candles, gap='1m')

    assert len(flagged) == 1
    assert bool(flagged.iloc[0]['flag']) is True
    assert flagged.iloc[0]['time'] == 180_000
    assert flagged.iloc[0]['gap_ms'] == 120_000


def test_upsert_candles_deduplicates_and_normalizes():
    candles = pd.DataFrame(
        {
            'symbol': ['BTCUSDT', 'BTCUSDT'],
            'time': [100, 100],
            'open': [10, 11],
            'high': [12, 13],
            'low': [9, 10],
            'close': [11, 12],
            'volume': [100, 200],
        }
    )

    records = upsert_candles(candles)

    assert len(records) == 1
    assert records[0]['close'] == 12
    assert records[0]['volume'] == 200
