# Roadmap

| Phase | Goal | Gate status |
| --- | --- | --- |
| P0 | Foundation, Docker stack, backfill, and live soak | **Passed** |
| P1 | Features and lifetime point-in-time validation | **In progress** |
| P2 | Labels, sample weights, and purge-safe splits | Not started |
| P3 | XGBoost baseline validation | Not started |
| P4 | Ensemble modeling | Not started |
| P5 | Serving and frontend integration | Not started |
| P6 | Drift monitoring and MLOps | Not started |

The project follows the exact gates in PROJECT_SPEC.md.

## P0 Gate Evidence

- Docker Compose stack: API, TimescaleDB, Valkey, MinIO, MLflow, and web services running; API/web/MLflow endpoints returned HTTP 200.
- Historical backfill: `files/btc_history_1m.parquet` contains 4,139,000 BTCUSDT 1m candles from `1502942400000` through `1751800260000`.
- Dataset integrity: 0 duplicates, 0 nulls in required OHLCV fields, and 0 OHLCV violations.
- Aggregate verification: 10/10 representative 1m-to-5m checks matched Binance 5m candles.
- Websocket soak: 300 messages, 10 closed candles, and 0 errors over 10 minutes.
- Gap scan: 35 non-contiguous intervals were reported for investigation; no values were filled and this does not affect the OHLCV violation gate.

## P1 Progress

- Explicit registry with 50 features implemented, including 43 technical and 7 derived features.
- Pure feature computation, causal derived features, and parquet materialization are covered by 4 focused tests.
- Price-action pattern and support/resistance utilities are implemented and covered by focused tests.
- Remaining P1 gate work: null-rate measurement after warmup, Feast latency, and 100-point point-in-time audit.
