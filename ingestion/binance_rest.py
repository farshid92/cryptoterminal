"""Binance REST ingestion helpers."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib import error, request


def _request_json(url: str, retries: int = 3, backoff: float = 0.5) -> Any:
    """Fetch JSON with lightweight retry/backoff handling."""
    for attempt in range(retries):
        try:
            with request.urlopen(url, timeout=30) as response:
                payload = response.read()
            return json.loads(payload.decode('utf-8'))
        except (error.URLError, ValueError, json.JSONDecodeError):
            if attempt == retries - 1:
                raise
            time.sleep(backoff * (2**attempt))
    raise RuntimeError('request failed unexpectedly')


def fetch_klines(sym, interval, start, end, max_pages: int | None = None):
    """Fetch OHLCV klines from Binance for the requested time window.

    Args:
        sym: symbol like BTCUSDT.
        interval: Binance interval string like 1m or 1h.
        start: start timestamp in epoch milliseconds.
        end: end timestamp in epoch milliseconds.

    Returns:
        A deduplicated list of candle dictionaries keyed by symbol/time.
    """
    symbol = str(sym).upper()
    interval_name = str(interval)
    rows: list[dict[str, Any]] = []
    limit = 1000
    start_ms = int(start)
    end_ms = int(end)
    pages = 0

    while start_ms < end_ms:
        url = (
            'https://api.binance.com/api/v3/klines?'
            f'symbol={symbol}&interval={interval_name}&startTime={start_ms}&endTime={end_ms}&limit={limit}'
        )
        payload = _request_json(url)
        if not payload:
            break

        for candle in payload:
            rows.append(
                {
                    'symbol': symbol,
                    'time': int(candle[0]),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]),
                    'quote_asset_volume': float(candle[7]),
                    'trades': int(candle[8]),
                    'taker_buy_base': float(candle[9]),
                    'taker_buy_quote': float(candle[10]),
                }
            )

        last_time = int(payload[-1][0])
        if last_time <= start_ms:
            break
        start_ms = last_time + 1
        pages += 1
        if max_pages is not None and pages >= max_pages:
            break

    deduped: dict[int, dict[str, Any]] = {}
    for row in rows:
        deduped[row['time']] = row

    return list(deduped.values())
