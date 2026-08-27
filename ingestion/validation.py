"""Validation helpers for backfilled OHLCV data."""

from __future__ import annotations

import pandas as pd


def aggregate_candles(frame: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Aggregate 1m candles into a higher timeframe."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=['symbol', 'time', 'open', 'high', 'low', 'close', 'volume'])
    if 'time' not in frame.columns:
        raise KeyError('frame must include time')

    interval_map = {
        '5m': '5min',
        '15m': '15min',
        '1h': '1h',
        '4h': '4h',
        '1d': '1d',
    }
    if interval not in interval_map:
        raise ValueError(f'unsupported interval: {interval}')

    working = frame.copy()
    working['datetime'] = pd.to_datetime(working['time'], unit='ms', utc=True)
    working = working.set_index('datetime')

    aggregated = (
        working.groupby('symbol')
        .resample(interval_map[interval])
        .agg(
            {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
            }
        )
        .dropna()
        .reset_index()
    )
    aggregated['time'] = aggregated['datetime'].astype('int64') // 10**6
    return aggregated[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]


def verify_aggregates(source_1m: pd.DataFrame, aggregate: pd.DataFrame, interval: str, sample_size: int = 10) -> pd.DataFrame:
    """Compare aggregated candles against a provided higher timeframe frame."""
    expected = aggregate_candles(source_1m, interval)
    if expected.empty or aggregate is None or aggregate.empty:
        return pd.DataFrame(columns=['time', 'matched', 'mismatch_count'])

    merged = expected.merge(aggregate, on=['symbol', 'time'], how='inner', suffixes=('_expected', '_actual'))
    if merged.empty:
        return pd.DataFrame(columns=['time', 'matched', 'mismatch_count'])

    rows = []
    columns = ['open', 'high', 'low', 'close', 'volume']
    for _, row in merged.head(sample_size).iterrows():
        mismatches = sum(float(row[f'{column}_expected']) != float(row[f'{column}_actual']) for column in columns)
        rows.append(
            {
                'time': int(row['time']),
                'matched': mismatches == 0,
                'mismatch_count': mismatches,
            }
        )
    return pd.DataFrame(rows)


def scan_ohlcv_violations(frame: pd.DataFrame) -> pd.DataFrame:
    """Identify OHLCV integrity violations in a candle frame."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=['time', 'violation'])
    required = {'open', 'high', 'low', 'close', 'volume', 'time'}
    missing = required.difference(frame.columns)
    if missing:
        missing_msg = ', '.join(sorted(missing))
        raise KeyError(f'missing required columns: {missing_msg}')

    violations = frame[
        (frame['high'] < frame[['open', 'close']].max(axis=1))
        | (frame['low'] > frame[['open', 'close']].min(axis=1))
        | (frame['volume'] < 0)
        | (frame['high'] < frame['low'])
    ].copy()
    if violations.empty:
        return pd.DataFrame(columns=['time', 'violation'])

    violations['violation'] = 'ohlcv_rule_broken'
    return violations[['time', 'violation']].reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    """Minimal CLI placeholder for backfill validation workflows."""
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
