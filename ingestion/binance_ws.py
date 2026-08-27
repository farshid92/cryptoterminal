"""Binance websocket ingestion worker."""

from __future__ import annotations

import argparse
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import websocket


def stream_url(symbol: str, interval: str) -> str:
    """Return the Binance combined kline stream URL."""
    return (
        'wss://stream.binance.com:9443/ws/'
        f'{symbol.lower()}@kline_{interval.lower()}'
    )


def parse_kline_message(message: str) -> dict[str, Any]:
    """Parse a Binance kline websocket payload into a candle snapshot."""
    payload = json.loads(message)
    if 'k' not in payload:
        raise ValueError('message does not contain kline data')

    kline = payload['k']
    return {
        'symbol': str(payload['s']).upper(),
        'time': int(kline['t']),
        'open': float(kline['o']),
        'high': float(kline['h']),
        'low': float(kline['l']),
        'close': float(kline['c']),
        'volume': float(kline['v']),
        'is_closed': bool(kline['x']),
    }


@dataclass
class StreamStats:
    """Mutable counters for a websocket soak session."""

    messages: int = 0
    closed_candles: int = 0
    first_time: int | None = None
    last_time: int | None = None
    errors: list[str] = field(default_factory=list)


def connect_stream(
    symbol: str = 'BTCUSDT',
    interval: str = '1m',
    duration_s: int = 600,
    on_message: Callable[[dict[str, Any]], None] | None = None,
) -> StreamStats:
    """Connect to Binance websocket and collect stream statistics.

    Args:
        symbol: Binance symbol, default BTCUSDT.
        interval: Binance kline interval.
        duration_s: number of seconds to keep the stream open.
        on_message: optional callback for each parsed kline event.

    Returns:
        StreamStats with message counts and observed timestamps.
    """
    if duration_s <= 0:
        raise ValueError('duration_s must be positive')

    stats = StreamStats()
    done = threading.Event()

    def handle_message(_: websocket.WebSocketApp, message: str) -> None:
        event = parse_kline_message(message)
        stats.messages += 1
        stats.first_time = event['time'] if stats.first_time is None else stats.first_time
        stats.last_time = event['time']
        if event['is_closed']:
            stats.closed_candles += 1
        if on_message is not None:
            on_message(event)

    def handle_error(_: websocket.WebSocketApp, error: Exception) -> None:
        stats.errors.append(str(error))
        done.set()

    def handle_close(_: websocket.WebSocketApp, __code: Any, __msg: Any) -> None:
        done.set()

    app = websocket.WebSocketApp(
        stream_url(symbol, interval),
        on_message=handle_message,
        on_error=handle_error,
        on_close=handle_close,
    )

    thread = threading.Thread(target=app.run_forever, kwargs={'ping_interval': 20, 'ping_timeout': 10}, daemon=True)
    thread.start()
    done.wait(timeout=duration_s)
    app.close()
    thread.join(timeout=5)
    return stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run a Binance websocket soak session.')
    parser.add_argument('--symbol', default='BTCUSDT')
    parser.add_argument('--interval', default='1m')
    parser.add_argument('--duration-s', type=int, default=600)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stats = connect_stream(args.symbol, args.interval, args.duration_s)
    print(
        f'messages={stats.messages} closed={stats.closed_candles} '
        f'first_time={stats.first_time} last_time={stats.last_time} errors={len(stats.errors)}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
