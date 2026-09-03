# cryptoterminal

Bitcoin-first signal-generation research project.

## Scope

This repository implements the signal-only research pipeline defined in PROJECT_SPEC.md:

- public-market data ingestion
- point-in-time feature generation
- leakage-safe labeling and artifact construction
- walk-forward evaluation and metric gating
- signal scoring for research and validation only

This project does not execute trades, connect to a broker, place orders, or manage wallet funds.

## Current status

- Phase 0: complete
- Phase 1: complete
- Phase 2: complete
- Phase 3: validation is blocked on full long-window gate evidence; the signal-only architecture remains in place

## Canonical references

- [PROJECT_SPEC.md](PROJECT_SPEC.md) — source of truth for constraints, phase gates, and project rules
- [docs/ROADMAP.md](docs/ROADMAP.md) — current status, progress, and gate evidence

## Repository layout

- `ingestion/` — public Binance ingestion and validation
- `features/` — technical and causal feature engineering
- `labeling/` — triple-barrier labels, sample weights, and holdout-safe splits
- `models/` — baselines, ranking model, and validation logic
- `backtest/` — strategy metrics and gate checks
- `files/` — generated parquet artifacts
- `tests/` — focused validation for each project phase
- `infra/` — local Docker stack
- `docs/` — active project documentation only

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e .
pytest -q
```
