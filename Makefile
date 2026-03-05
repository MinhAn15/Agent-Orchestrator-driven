# ============================================================================
# Antigravity — Makefile
# ============================================================================
.DEFAULT_GOAL := help
PYTHON ?= python
VENV := .venv

# ── Setup ────────────────────────────────────────────────────────
.PHONY: setup
setup: ## Create venv and install all dependencies
	$(PYTHON) -m venv $(VENV)
	$(VENV)/Scripts/pip install --upgrade pip || $(VENV)/bin/pip install --upgrade pip
	$(VENV)/Scripts/pip install -e ".[dev]" || $(VENV)/bin/pip install -e ".[dev]"
	@echo "✅ Setup complete. Activate: source $(VENV)/bin/activate  OR  $(VENV)\\Scripts\\Activate.ps1"

# ── Quality ──────────────────────────────────────────────────────
.PHONY: lint
lint: ## Run ruff linter
	ruff check .

.PHONY: format
format: ## Auto-format code with ruff
	ruff check --fix .
	ruff format .

.PHONY: typecheck
typecheck: ## Run mypy type checker
	mypy

.PHONY: test
test: ## Run pytest with coverage
	pytest -q

.PHONY: quality
quality: lint typecheck test ## Run full quality pipeline (lint + typecheck + test)

# ── Demo ─────────────────────────────────────────────────────────
.PHONY: demo
demo: ## Run quickstart demo
	$(PYTHON) examples/quickstart.py

.PHONY: cli-demo
cli-demo: ## Run CLI ad-hoc demo
	$(PYTHON) -m antigravity.cli run incident-response \
		--vars '{"team":"SRE","service":"payments-api","severity":"P1"}' \
		--context '{"environment":"production","data_classification":"confidential"}'

# ── MCP Server ───────────────────────────────────────────────────
.PHONY: mcp
mcp: ## Start MCP stdio server
	$(PYTHON) -m antigravity.cli mcp --stdio

# ── Docs ─────────────────────────────────────────────────────────
.PHONY: docs
docs: ## Build documentation
	mkdocs build --strict

.PHONY: docs-serve
docs-serve: ## Serve documentation locally
	mkdocs serve

# ── Benchmarks ───────────────────────────────────────────────────
.PHONY: bench
bench: ## Run benchmarks
	$(PYTHON) benchmarks/run_benchmarks.py

# ── Cleanup ──────────────────────────────────────────────────────
.PHONY: clean
clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .mypy_cache .ruff_cache .pytest_cache htmlcov .coverage site/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ── Help ─────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
