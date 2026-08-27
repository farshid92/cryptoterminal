"""Historical backfill helpers for Binance OHLCV data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.binance_rest import fetch_klines
from ingestion.writers import upsert_candles


def _interval_to_ms(interval: str) -> int:
    """Convert a Binance interval string to milliseconds."""
    value = str(interval).strip().lower()
    units = {
        '1m': 60_000,
        '5m': 5 * 60_000,
        '15m': 15 * 60_000,
        '1h': 60 * 60_000,
        '4h': 4 * 60 * 60_000,
        '1d': 24 * 60 * 60 * 1000,
    }
    if value not in units:
        raise ValueError(f'unsupported interval: {interval}')
    return units[value]


def backfill_ohlcv(symbol: str, interval: str, start_ms: int = 0, end_ms: int | None = None) -> pd.DataFrame:
    """Fetch a full OHLCV history window and return a normalized dataframe."""
    symbol_name = str(symbol).upper()
    interval_ms = _interval_to_ms(interval)
    stop_ms = int(end_ms) if end_ms is not None else int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    cursor_ms = int(start_ms)
    rows: list[dict[str, Any]] = []

    while cursor_ms < stop_ms:
        batch = fetch_klines(symbol_name, interval, cursor_ms, stop_ms)
        if not batch:
            break

        rows.extend(batch)
        last_time = max(int(row['time']) for row in batch)
        next_cursor = last_time + interval_ms
        if next_cursor <= cursor_ms:
            break
        cursor_ms = next_cursor

    normalized = pd.DataFrame(upsert_candles(pd.DataFrame(rows)))
    if normalized.empty:
        return pd.DataFrame(columns=['symbol', 'time', 'open', 'high', 'low', 'close', 'volume'])

    normalized = normalized.sort_values('time').reset_index(drop=True)
    return normalized


def save_parquet(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Persist a normalized backfill frame to parquet."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Backfill OHLCV candles from Binance public REST.')
    parser.add_argument('--symbol', default='BTCUSDT')
    parser.add_argument('--interval', default='1m')
    parser.add_argument('--start-ms', type=int, default=0)
    parser.add_argument('--end-ms', type=int)
    parser.add_argument('--output', help='Optional parquet output path')
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    frame = backfill_ohlcv(args.symbol, args.interval, start_ms=args.start_ms, end_ms=args.end_ms)
    if args.output:
        save_parquet(frame, args.output)
    print(f'rows={len(frame)} symbol={args.symbol} interval={args.interval}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
