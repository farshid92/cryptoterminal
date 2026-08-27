#!/usr/bin/env bash
set -euo pipefail

python -m ingestion.backfill "$@"
