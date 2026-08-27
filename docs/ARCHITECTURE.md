# Architecture

This repository is designed around the canonical pipeline described in PROJECT_SPEC.md.

## Core flow

1. Ingestion pulls raw OHLCV data from Binance public APIs.
2. Feature builders compute technical and market-state features.
3. Labels are generated using triple-barrier logic.
4. Models are trained and evaluated in backtests.
5. The signal engine serves the final output through FastAPI and websocket fanout.

## Service boundaries

- Ingestion: public data download and storage
- Features: pure feature computations and feature registry
- Labels: event-based labeling
- Models: training, prediction, and ONNX export
- Serving: APIs and live signals
- MLOps: monitoring and retraining
