# cryptoterminal

Bitcoin-first daily trading analysis system.

## Overview

This repository is intended to implement the full research and signal pipeline described in PROJECT_SPEC.md:

- data ingestion from public APIs
- feature engineering and point-in-time validation
- labeling and walk-forward evaluation
- model training and ensemble experiments
- serving and monitoring

## Current status

Phase 0 foundation scaffold is being initialized. The project is intentionally organized around the canonical structure defined in the spec.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e .
make test
```

## Repository structure

- `ingestion/` - market data ingestion and writers
- `features/` - technical and price-action features
- `labeling/` - labels and sample weights
- `models/` - baselines, classifiers, and model exports
- `backtest/` - validation and evaluation
- `serving/` - FastAPI and signal serving
- `web/` - Next.js dashboard
- `infra/` - Docker Compose services
- `docs/` - architecture and API contracts

## Policy

This project never executes trades. It produces analysis and signals only.
