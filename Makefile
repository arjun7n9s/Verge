# Verge — developer entrypoints
.DEFAULT_GOAL := help
COMPOSE := docker compose -f deploy/docker-compose.yml --env-file deploy/.env
COMPOSE_APP := $(COMPOSE) --profile app

.PHONY: help install up up-app down logs seed dev api console eval test lint fmt demo-live ci

install: ## Set up the workspace (uv sync + pnpm install)
	uv sync
	pnpm install

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Bring up infra (Redpanda, Postgres/PostGIS, Timescale, Neo4j, MinIO, Keycloak, Redis)
	$(COMPOSE) up -d

up-app: ## Infra + API + console (compose profile `app`, builds images)
	$(COMPOSE_APP) up -d --build

down: ## Tear down infra
	$(COMPOSE) down

logs: ## Tail infra logs
	$(COMPOSE) logs -f --tail=100

seed: ## (Re)generate the Vizag replay dataset
	uv run python eval/replays/vizag-2025-01/generate.py

dev: ## Run api + console (dev)
	$(MAKE) -j2 api console

dev-sql: ## Run API with SQL store (Postgres from make up)
	VERGE_STORE=sql VERGE_DB_URL=postgresql+psycopg://verge:changeme@localhost:5432/verge uv run uvicorn verge_api.main:app --reload --port 8000

api: ## Run the FastAPI gateway
	uv run uvicorn verge_api.main:app --reload --port 8000

console: ## Run the operator console (Vite)
	pnpm --filter @verge/console dev

eval: ## Run the replay harness vs baselines B0/B1/B2
	uv run verge replay --all

demo-live: ## Live path: sim stream -> risk-engine -> API (needs api on :8000)
	uv run verge sim --scenario vizag-like | uv run python -m verge_risk --post http://localhost:8000

test: ## Run the Python test suite
	uv run pytest

lint: ## Lint (ruff + console typecheck)
	uv run ruff check .
	pnpm --filter @verge/console typecheck

fmt: ## Format (ruff format)
	uv run ruff format .

ci: ## Mirror GitHub Actions (lint, test, eval replays, console build)
	uv run ruff check .
	uv run pytest
	@for f in eval/replays/*/generate.py; do uv run python "$$f"; done
	uv run verge replay --all
	pnpm --filter @verge/console typecheck
	pnpm --filter @verge/console build
