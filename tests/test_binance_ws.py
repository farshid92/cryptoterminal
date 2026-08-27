import json

from ingestion.binance_ws import parse_kline_message, stream_url


def test_stream_url_builds_binance_kline_endpoint():
    assert stream_url('BTCUSDT', '1m') == 'wss://stream.binance.com:9443/ws/btcusdt@kline_1m'


def test_parse_kline_message_extracts_candle_snapshot():
    payload = {
        's': 'BTCUSDT',
        'k': {
            't': 1700000000000,
            'o': '100.0',
            'h': '101.0',
            'l': '99.0',
            'c': '100.5',
            'v': '123.45',
            'x': True,
        },
    }

    parsed = parse_kline_message(json.dumps(payload))

    assert parsed['symbol'] == 'BTCUSDT'
    assert parsed['time'] == 1700000000000
    assert parsed['close'] == 100.5
    assert parsed['is_closed'] is True
