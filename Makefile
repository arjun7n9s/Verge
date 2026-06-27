# Verge — developer entrypoints
.DEFAULT_GOAL := help
COMPOSE := docker compose -f deploy/docker-compose.yml --env-file deploy/.env

.PHONY: help up down logs seed dev api console eval test lint fmt

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Bring up infra (Redpanda, Postgres/PostGIS, Timescale, Neo4j, MinIO, Keycloak, Redis)
	$(COMPOSE) up -d

down: ## Tear down infra
	$(COMPOSE) down

logs: ## Tail infra logs
	$(COMPOSE) logs -f --tail=100

seed: ## Load demo plant + Vizag replay
	python -m verge_cli seed --plant demo

dev: ## Run api + console (dev)
	$(MAKE) -j2 api console

api: ## Run the FastAPI gateway
	uvicorn verge_api.main:app --reload --port 8000 --app-dir services/api

console: ## Run the operator console (Vite)
	pnpm --filter @verge/console dev

eval: ## Run the replay harness vs baselines B0/B1/B2
	python -m eval.harness --all

test: ## Run the Python test suite
	pytest -q

lint: ## Lint (ruff + tsc)
	ruff check . && pnpm -r exec tsc --noEmit

fmt: ## Format (ruff format)
	ruff format .
