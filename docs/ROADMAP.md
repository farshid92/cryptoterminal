# Roadmap

| Phase | Goal | Gate status |
| --- | --- | --- |
| P0 | Foundation, Docker stack, backfill, and live soak | **Passed** |
| P1 | Features and lifetime point-in-time validation | **Passed** |
| P2 | Labels, sample weights, and purge-safe splits | **Passed** |
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
- Real backfill null-rate measurement: maximum post-warmup null rate is 1.36%, with no feature above the 5% threshold.
- Point-in-time audit helper is implemented and tested on 20 deterministic samples.
- Real-data PIT audit: 100/100 samples matched on a 50,000-row backfill window in 41.05 seconds.
- Optimized full-data PIT audit: 100/100 samples matched across all 4,139,000 rows in 129.69 seconds.
- Feast serving support is installed at version 0.66.0 and declared in the project dependencies.
- Feast repository setup and benchmark tooling are implemented and covered by a repository-creation test.
- Feast complete-frame local SQLite benchmark: 4,139,000 feature rows materialized; 1,000 online retrievals measured p50 0.655 ms and p99 1.601 ms, below the 5 ms target.
- P1 gate criteria are now met; P1 closure is pending final documentation and commit.

## P2 Progress

- Triple-barrier labels are implemented with first-touch ordering, horizon expiry, and return outputs.
- Sample weights are implemented with uniqueness, return magnitude, and optional time-decay components.
- Purge/embargo behavior is covered by an overlap-proof test.
- Class-distribution reporting and a chronological last-six-month holdout splitter are implemented and tested.
- Real latest-200,000-row label distribution with contract defaults is `{-1: 61.59%, 0: 0.10%, 1: 38.31%}`, so the default profile fails the required 25–45% balance criterion.
- An explicit symmetric `tp_m=6.0`, `sl_m=6.0`, `horizon=60` profile produces `{-1: 32.30%, 0: 34.88%, 1: 32.82%}` on the same window and passes the balance bounds; defaults remain unchanged.
- Full-dataset holdout split contains 3,878,359 training rows and 260,641 holdout rows with no timestamp overlap.
- The balanced profile is now explicit as `BALANCED_LABELING_CONFIG`; contract defaults remain unchanged.
- Holdout exclusion is enforced by a reusable timestamp-overlap assertion.
- Real-data validation with `BALANCED_LABELING_CONFIG` passes: `{-1: 32.30%, 0: 34.88%, 1: 32.82%}` and holdout timestamp overlap is zero.
- Leakage-safe training-artifact builder now labels and weights only the pre-holdout partition, persists parquet, and asserts timestamp exclusion.
- Real artifact sample: 242,581 pre-holdout rows persisted from a 500,000-row source window with zero timestamp overlap against 257,419 holdout rows.
- Triple-barrier labeling now uses a cached Numba kernel for the exact existing semantics; full artifact generation is ready for a performance-checked run.
- Full-history barrier search shows no fixed barrier profile satisfies the class-balance gate across all regimes; training artifacts now use deterministic undersampling to the smallest class after labeling.
- Full balanced training artifact `files/p2_training_full_balanced.parquet` persists 2,666,883 pre-holdout rows.
- Final artifact distribution is exactly `{-1: 33.33%, 0: 33.33%, 1: 33.33%}`, passing the 25–45% class-balance gate.
- Final artifact training maximum timestamp is `1736161620000`, before the holdout minimum `1736161860000`; timestamp overlap is zero.
- Deterministic undersampling uses seed 42 and preserves chronological ordering after sampling.
- P2 gate criteria are met and P2 is closed.

## P3 Progress

- Deterministic signal-only baselines are implemented: buy-and-hold, random, RSI reversal, and SMA crossover.
- P3 strategy metrics now include Sharpe, maximum drawdown, profit factor, and non-neutral signal coverage.
- XGBoost multiclass wrapper is implemented with stable `-1, 0, 1` label encoding and probability output.
- Optuna tuning entry point is configured for the required 200 chronological validation trials.
- MLflow metric logging is implemented for baseline and model runs.
- P3 acceptance evidence is not complete yet; walk-forward tuning and gate metrics remain to be run on the full feature artifact.
