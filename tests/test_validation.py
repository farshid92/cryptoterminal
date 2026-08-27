import pandas as pd

from ingestion.validation import aggregate_candles, scan_ohlcv_violations, verify_aggregates


def test_aggregate_candles_rolls_1m_rows_into_higher_timeframe():
    frame = pd.DataFrame(
        {
            'symbol': ['BTCUSDT'] * 5,
            'time': [0, 60_000, 120_000, 180_000, 240_000],
            'open': [1, 2, 3, 4, 5],
            'high': [2, 3, 4, 5, 6],
            'low': [0.5, 1.5, 2.5, 3.5, 4.5],
            'close': [1.5, 2.5, 3.5, 4.5, 5.5],
            'volume': [10, 11, 12, 13, 14],
        }
    )

    aggregated = aggregate_candles(frame, '5m')

    assert len(aggregated) == 1
    assert aggregated.iloc[0]['open'] == 1
    assert aggregated.iloc[0]['high'] == 6
    assert aggregated.iloc[0]['low'] == 0.5
    assert aggregated.iloc[0]['close'] == 5.5
    assert aggregated.iloc[0]['volume'] == 60


def test_verify_aggregates_reports_matching_rows():
    source = pd.DataFrame(
        {
            'symbol': ['BTCUSDT'] * 5,
            'time': [0, 60_000, 120_000, 180_000, 240_000],
            'open': [1, 2, 3, 4, 5],
            'high': [2, 3, 4, 5, 6],
            'low': [0.5, 1.5, 2.5, 3.5, 4.5],
            'close': [1.5, 2.5, 3.5, 4.5, 5.5],
            'volume': [10, 11, 12, 13, 14],
        }
    )
    aggregate = aggregate_candles(source, '5m')

    report = verify_aggregates(source, aggregate, '5m', sample_size=10)

    assert len(report) == 1
    assert bool(report.iloc[0]['matched']) is True
    assert report.iloc[0]['mismatch_count'] == 0


def test_scan_ohlcv_violations_flags_bad_candles():
    frame = pd.DataFrame(
        {
            'time': [0, 60_000],
            'open': [10, 10],
            'high': [12, 9],
            'low': [9, 11],
            'close': [11, 10],
            'volume': [1, -1],
        }
    )

    violations = scan_ohlcv_violations(frame)

    assert len(violations) == 1
    assert set(violations['violation']) == {'ohlcv_rule_broken'}
