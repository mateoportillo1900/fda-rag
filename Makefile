# Requires Git Bash or WSL on Windows.
# From PowerShell, run the underlying commands directly (see comments).
.PHONY: setup download-sample download-full test lint format eval db-up db-down

## Bootstrap: copy .env template (skips if .env already exists) and install all deps
setup:
	cp -n .env.example .env || true
	uv sync --extra dev

## Download 10 curated sample labels → data/sample/xml/ (safe to commit, ~2-4 MB)
download-sample:
	uv run scripts/download_dailymed.py --sample

## Download all 50 curated labels → data/raw/xml/ (gitignored, ~25-40 MB)
download-full:
	uv run scripts/download_dailymed.py

## Create the drug_chunks table in Neon (run once)
migrate:
	uv run scripts/migrate.py

## Run the full ingestion pipeline against data/sample/xml/
ingest:
	uv run scripts/run_ingestion.py

## Run the full test suite
test:
	uv run pytest tests/ -v

## Lint (reports only; use `format` to auto-fix)
lint:
	uv run ruff check src/ tests/

## Auto-format and fix lint issues
format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

## Placeholder — RAGAS eval harness arrives in week 6
eval:
	@echo "No eval harness yet — coming in week 6"

# ── Local Docker targets (optional — only needed if you have Docker Desktop) ──
## Start local Postgres container (Docker Desktop required)
db-up:
	docker compose up -d --wait

## Stop local Postgres container (data volume is preserved)
db-down:
	docker compose down
