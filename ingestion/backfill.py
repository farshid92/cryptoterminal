"""Historical backfill helpers for Binance OHLCV data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

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


def backfill_ohlcv(
    symbol: str,
    interval: str,
    start_ms: int = 0,
    end_ms: int | None = None,
    max_batches: int | None = None,
) -> pd.DataFrame:
    """Fetch a full OHLCV history window and return a normalized dataframe."""
    symbol_name = str(symbol).upper()
    interval_ms = _interval_to_ms(interval)
    stop_ms = int(end_ms) if end_ms is not None else int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    cursor_ms = int(start_ms)
    rows: list[dict[str, Any]] = []
    batches = 0

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
        batches += 1
        if max_batches is not None and batches >= max_batches:
            break

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


def _table_from_frame(frame: pd.DataFrame) -> pa.Table:
    """Convert a dataframe to a pyarrow table."""
    return pa.Table.from_pandas(frame, preserve_index=False)


def stream_backfill_to_parquet(
    symbol: str,
    interval: str,
    output_path: str | Path,
    start_ms: int = 0,
    end_ms: int | None = None,
) -> int:
    """Stream pages from Binance directly into a parquet file."""
    symbol_name = str(symbol).upper()
    interval_ms = _interval_to_ms(interval)
    stop_ms = int(end_ms) if end_ms is not None else int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    cursor_ms = int(start_ms)
    total_rows = 0
    writer: pq.ParquetWriter | None = None
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        while cursor_ms < stop_ms:
            batch = fetch_klines(symbol_name, interval, cursor_ms, stop_ms, max_pages=1)
            if not batch:
                break

            frame = pd.DataFrame(upsert_candles(pd.DataFrame(batch)))
            if not frame.empty:
                table = _table_from_frame(frame)
                if writer is None:
                    writer = pq.ParquetWriter(path, table.schema)
                writer.write_table(table)
                total_rows += len(frame)

            last_time = max(int(row['time']) for row in batch)
            next_cursor = last_time + interval_ms
            if next_cursor <= cursor_ms:
                break
            cursor_ms = next_cursor
    finally:
        if writer is None and not path.exists():
            pd.DataFrame(columns=['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']).to_parquet(path, index=False)
        if writer is not None:
            writer.close()

    return total_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Backfill OHLCV candles from Binance public REST.')
    parser.add_argument('--symbol', default='BTCUSDT')
    parser.add_argument('--interval', default='1m')
    parser.add_argument('--start-ms', type=int, default=0)
    parser.add_argument('--end-ms', type=int)
    parser.add_argument('--max-batches', type=int)
    parser.add_argument('--output', help='Optional parquet output path')
    parser.add_argument('--stream-output', action='store_true', help='Stream pages into parquet without holding all rows in memory')
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.output and args.stream_output:
        rows = stream_backfill_to_parquet(
            args.symbol,
            args.interval,
            args.output,
            start_ms=args.start_ms,
            end_ms=args.end_ms,
        )
        print(f'rows={rows} symbol={args.symbol} interval={args.interval}')
        return 0

    frame = backfill_ohlcv(args.symbol, args.interval, start_ms=args.start_ms, end_ms=args.end_ms, max_batches=args.max_batches)
    if args.output:
        save_parquet(frame, args.output)
    print(f'rows={len(frame)} symbol={args.symbol} interval={args.interval}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
