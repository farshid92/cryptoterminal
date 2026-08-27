"""Gap detection for missing candles."""

from __future__ import annotations

import pandas as pd


def _gap_to_ms(gap: str) -> int:
    """Convert a gap string to milliseconds."""
    normalized = str(gap).lower().replace(' ', '')
    if normalized in {'1m', '1min'}:
        return 60_000
    if normalized in {'5m', '5min'}:
        return 5 * 60_000
    if normalized in {'15m', '15min'}:
        return 15 * 60_000
    if normalized in {'1h', '1hr', '60m'}:
        return 60 * 60_000
    raise ValueError(f'Unsupported gap value: {gap}')


def scan(table, gap='1min'):
    """Return rows with gaps exceeding the requested interval; no values are filled."""
    if table is None or table.empty:
        return pd.DataFrame(columns=['symbol', 'time', 'expected_time', 'gap_ms', 'flag'])

    frame = table.copy()
    if 'time' not in frame.columns:
        raise KeyError('table must include a time column')

    if 'symbol' not in frame.columns:
        frame['symbol'] = 'UNKNOWN'

    frame = frame.sort_values('time').reset_index(drop=True)
    frame['gap_ms'] = frame['time'].diff().fillna(0)
    gap_ms = _gap_to_ms(gap)
    flagged = frame[frame['gap_ms'] > gap_ms].copy()
    if flagged.empty:
        return flagged[['symbol', 'time', 'gap_ms']].assign(expected_time=pd.Series(dtype='float64'), flag=False)

    flagged['expected_time'] = flagged['time'] - flagged['gap_ms']
    flagged['flag'] = True
    return flagged[['symbol', 'time', 'expected_time', 'gap_ms', 'flag']].reset_index(drop=True)
