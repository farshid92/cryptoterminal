PYTHON ?= python

.PHONY: setup install lint test up down

setup:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -e .

install:
	. .venv/bin/activate && pip install -e .

lint:
	. .venv/bin/activate && ruff check .

test:
	. .venv/bin/activate && pytest -q

up:
	docker compose -f infra/docker-compose.yml up -d

down:
	docker compose -f infra/docker-compose.yml down
