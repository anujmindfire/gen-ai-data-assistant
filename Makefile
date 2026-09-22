.PHONY: help up down logs test lint format setup clean

help:
	@echo "GenAI Data Assistant - Monorepo Commands:"
	@echo "  make setup   - Initialize python environment and setup local dependencies"
	@echo "  make up      - Spin up all Docker Compose services (API, PostgreSQL, Qdrant)"
	@echo "  make down    - Stop and tear down Docker Compose services"
	@echo "  make logs    - Follow service logs from Docker Compose"
	@echo "  make test    - Run pytest suite in apps/api"
	@echo "  make lint    - Run Ruff linter across monorepo codebase"
	@echo "  make format  - Run Ruff auto-formatter across monorepo codebase"
	@echo "  make clean   - Remove cache files, build artifacts, and temp files"

setup:
	@bash scripts/setup.sh

up:
	docker compose -f infra/docker-compose.yml up --build -d

down:
	docker compose -f infra/docker-compose.yml down

logs:
	docker compose -f infra/docker-compose.yml logs -f

test:
	cd apps/api && uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
