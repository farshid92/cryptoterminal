# API Contracts

## REST

- GET /api/v1/health
- GET /api/v1/candles/{sym}?interval&limit
- GET /api/v1/indicators/{sym}?tf
- GET /api/v1/signal/{sym}?tf
- GET /api/v1/analysis/{sym}?tf
- POST /api/v1/backtests
- GET /api/v1/backtests/{id}

## WebSocket

- /ws/prices
- /ws/signals

This file is intentionally seeded with the contract requirements from PROJECT_SPEC.md and will be expanded as APIs are implemented.
