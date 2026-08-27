"""Writers for OHLCV and downstream state."""

from __future__ import annotations

import pandas as pd


def upsert_candles(df):
    """Normalize and deduplicate OHLCV rows for storage upserts."""
    if df is None or df.empty:
        return []

    frame = df.copy()
    required = {'time', 'open', 'high', 'low', 'close', 'volume'}
    missing = required.difference(frame.columns)
    if missing:
        missing_msg = ', '.join(sorted(missing))
        raise ValueError(f'missing required columns: {missing_msg}')

    frame['time'] = pd.to_numeric(frame['time'], errors='raise').astype('int64')
    for column in ['open', 'high', 'low', 'close', 'volume']:
        frame[column] = pd.to_numeric(frame[column], errors='raise')

    if 'symbol' in frame.columns:
        frame = frame.sort_values(['symbol', 'time']).drop_duplicates(subset=['symbol', 'time'], keep='last')
    else:
        frame = frame.sort_values('time').drop_duplicates(subset=['time'], keep='last')

    return frame.to_dict(orient='records')
