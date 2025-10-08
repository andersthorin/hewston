.DEFAULT_GOAL := help

# -------- Variables --------
PYTHON := uv run
UV := uv
NODE := node
NPM := npm
BACKEND_DIR := backend
FRONTEND_DIR := frontend
BFF_DIR := bff
CATALOG_DB := data/catalog.db
# default envs for local dev (override as needed)
DATABENTO_API_KEY ?= test-key
HEWSTON_CATALOG_PATH ?= data/catalog.db
HEWSTON_DATA_DIR ?= data

# Defaults (override on CLI: make data SYMBOL=AAPL YEAR=2023)
# These match the baseline values in docs/prd/features/00-baselines.md
SYMBOL ?= AAPL
YEAR ?= 2023
FROM ?=
TO ?=
STRATEGY ?= sma_crossover
FAST ?= 20
SLOW ?= 50
SPEED ?= 60
SYMBOLS ?= ALL

TF ?= 1Min
FORMAT ?= parquet
FILL_GAPS ?=
RTH_ONLY ?=

SEED ?= 42

# Backfill/materialize defaults
DATE ?=
START ?=
END ?=
VENUE ?= XNAS
WORKERS ?= 4

# -------- Meta --------
.PHONY: help
help:
	@echo "Hewston Make targets"
	@echo "  setup           Create Python venv (uv), prepare frontend (npm)"
	@echo "  start           Start backend API, BFF service, and frontend dev server"
	@echo "  start-backend   Start FastAPI backend server (uvicorn)"
	@echo "  start-bff       Start BFF service (uvicorn)"
	@echo "  start-frontend  Start Vite dev server"
	@echo "  stop            Stop backend, BFF, and frontend dev servers"
	@echo "  restart         Restart all services (stop→start)"
	@echo "  materialize-day   Build Quotes+Trades → MID bars for one day (SYMBOL=... DATE=YYYY-MM-DD VENUE=XNAS)"
	@echo "  backfill-warehouse Backfill warehouse over a date range (START=... END=... SYMBOLS='AAPL MSFT ...' VENUE=XNAS WORKERS=4)"
	@echo "  data            Ingest Databento DBN assets (SYMBOL, YEAR)"
	@echo "  backtest        Run baseline backtest and write artifacts"
	@echo "  db-init         Initialize SQLite catalog (see docs/architecture.md)"
	@echo "  db-apply        Apply SQLite schema to $(CATALOG_DB)"
	@echo "  lint            Run linters (ruff/eslint)"
	@echo "  format          Run formatters (black/prettier)"
	@echo "  test            Run tests (pytest/vitest)"
	@echo "  env             Print tool versions"
	@echo "  clean           Remove caches and temp files"
		@echo "  ci             Run full repo checks (backend+bff+frontend)"

# -------- Setup --------
.PHONY: setup
setup:
	@echo "[setup] Python venv via uv (.venv)" && \
	$(UV) venv --python 3.11 && \
	echo "[setup] (Optional) Install backend deps: uv pip install -r backend/requirements.txt" && \
	echo "[setup] (Optional) Create frontend: cd frontend && npm install"

# -------- Start / Dev --------
.PHONY: start

.PHONY: stop
stop:
	@echo "[stop] stopping servers on ports 8000, 8001, 5173-5174" && \
	pids=`lsof -nP -iTCP:8000,8001,5173-5174 -sTCP:LISTEN -t 2>/dev/null || true`; \
	if [ -n "$$pids" ]; then \
	  echo "[stop] killing $$pids"; \
	  kill $$pids 2>/dev/null || true; \
	  sleep 0.5; \
	  pids2=`lsof -nP -iTCP:8000,8001,5173-5174 -sTCP:LISTEN -t 2>/dev/null || true`; \
	  if [ -n "$$pids2" ]; then echo "[stop] force killing $$pids2"; kill -9 $$pids2 2>/dev/null || true; fi; \
	else \
	  echo "[stop] no listeners found"; \
	fi

.PHONY: restart
restart:
	@$(MAKE) stop
	@$(MAKE) -j3 start-backend start-bff start-frontend

start:
	@$(MAKE) -j3 start-backend start-bff start-frontend

.PHONY: start-backend
start-backend:
	@test -d $(BACKEND_DIR) && \
	  (echo "[backend] starting uvicorn"; \
	   export DATABENTO_API_KEY=$(DATABENTO_API_KEY) HEWSTON_CATALOG_PATH=$(HEWSTON_CATALOG_PATH) HEWSTON_DATA_DIR=$(HEWSTON_DATA_DIR); \
	   if [ -x .venv/bin/uvicorn ]; then \
	     .venv/bin/uvicorn $(BACKEND_DIR).app.main:app --reload --host 127.0.0.1 --port 8000; \
	   elif command -v uv >/dev/null 2>&1; then \
	     uv run uvicorn $(BACKEND_DIR).app.main:app --reload --host 127.0.0.1 --port 8000; \
	   else \
	     python3 -m uvicorn $(BACKEND_DIR).app.main:app --reload --host 127.0.0.1 --port 8000; \
	   fi ) \
	|| (echo "[backend] missing $(BACKEND_DIR)/ — scaffold later" && true)

.PHONY: start-bff
start-bff:
	@test -d $(BFF_DIR) && \
	  (echo "[bff] starting uvicorn"; \
	   export HEWSTON_BACKEND_URL=http://127.0.0.1:8000 BFF_LOG_LEVEL=INFO; \
	   if [ -x .venv/bin/uvicorn ]; then \
	     .venv/bin/uvicorn $(BFF_DIR).app.main:app --reload --host 127.0.0.1 --port 8001; \
	   elif command -v uv >/dev/null 2>&1; then \
	     uv run uvicorn $(BFF_DIR).app.main:app --reload --host 127.0.0.1 --port 8001; \
	   else \
	     python3 -m uvicorn $(BFF_DIR).app.main:app --reload --host 127.0.0.1 --port 8001; \
	   fi ) \
	|| (echo "[bff] missing $(BFF_DIR)/ — scaffold later" && true)

.PHONY: start-frontend
start-frontend:
	@test -d $(FRONTEND_DIR) && \
	  (echo "[frontend] starting vite" && \
	   cd $(FRONTEND_DIR) && { export NVM_DIR="$$HOME/.nvm"; [ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh" && nvm use 22 >/dev/null 2>&1 || true; } && \
	   $(NPM) run dev) \
	|| (echo "[frontend] missing $(FRONTEND_DIR)/ — scaffold later" && true)

# -------- Jobs (Typer) --------
.PHONY: data
data:
	@echo "[data] SYMBOL=$(SYMBOL) YEAR=$(YEAR)" && \
	test -d $(BACKEND_DIR) && \
	  $(PYTHON) -m $(BACKEND_DIR).jobs.cli data --symbol $(SYMBOL) --year $(YEAR) || \
	  (echo "[data] missing backend jobs; implement backend/jobs/cli.py" && false)

.PHONY: backtest
backtest:
	@echo "[backtest] $(SYMBOL) $(FROM)..$(TO) $(STRATEGY) fast=$(FAST) slow=$(SLOW) speed=$(SPEED) seed=$(SEED)" && \
	test -d $(BACKEND_DIR) && \
	  $(PYTHON) -m $(BACKEND_DIR).jobs.cli backtest \
	    --symbol $(SYMBOL) --from $(FROM) --to $(TO) \
			--strategy-id $(STRATEGY) --param fast=$(FAST) --param slow=$(SLOW) \
			--speed $(SPEED) --seed $(SEED) || \
		  (echo "[backtest] missing backend jobs; implement backend/jobs/cli.py" && false)


.PHONY: materialize-day
materialize-day:
		@if [ -z "$(SYMBOL)" ] || [ -z "$(DATE)" ]; then echo "[materialize-day] require SYMBOL and DATE=YYYY-MM-DD"; exit 2; fi; \
		IID=""; \
		case "$(SYMBOL)" in \
		  AAPL) IID=38 ;; \
		  MSFT) IID=10888 ;; \
		  GOOGL) IID=7152 ;; \
		  TSLA) IID=16244 ;; \
		  NVDA) IID=11667 ;; \
		  *) echo "[materialize-day] unknown SYMBOL $(SYMBOL)"; exit 2 ;; \
		esac; \
		YMD=$$(echo "$(DATE)" | tr -d -); \
		TBBO="data/raw/databento/tbbo/xnas-itch-$${YMD}.tbbo.dbn.zst"; \
		TRDB="data/raw/databento/trades/xnas-itch-$${YMD}.trades.dbn.zst"; \
		if [ ! -f "$$TBBO" ] || [ ! -f "$$TRDB" ]; then echo "[materialize-day] missing raw files: tbbo=$$TBBO exists=$$(test -f $$TBBO && echo yes || echo no) trades=$$TRDB exists=$$(test -f $$TRDB && echo yes || echo no)"; exit 3; fi; \
		echo "[run] quotes_ingest $(SYMBOL) $(DATE) IID=$$IID VENUE=$(VENUE)"; \
		$(PYTHON) backend/jobs/quotes_ingest.py "$$TBBO" --instrument-id "$$IID" --symbol "$(SYMBOL)" --venue "$(VENUE)" && \
		echo "[run] trades_aggregate $(SYMBOL) $(DATE) IID=$$IID VENUE=$(VENUE)"; \
		$(PYTHON) backend/jobs/trades_aggregate.py "$$TRDB" --instrument-id "$$IID" --symbol "$(SYMBOL)" --venue "$(VENUE)" && \
		echo "[run] materialize_bars $(SYMBOL) $(DATE) VENUE=$(VENUE)"; \
		$(PYTHON) backend/jobs/materialize_bars.py --symbol "$(SYMBOL)" --date "$(DATE)" --venue "$(VENUE)"

.PHONY: backfill-warehouse
backfill-warehouse:
		@SYMS=$$( if [ "$(SYMBOLS)" = "ALL" ]; then echo "AAPL MSFT GOOGL TSLA NVDA"; else echo "$(SYMBOLS)"; fi ); \
		echo "[backfill] $$SYMS $(START)..$(END) VENUE=$(VENUE) WORKERS=$(WORKERS)"; \
		$(PYTHON) scripts/backfill_warehouse.py --start "$(START)" --end "$(END)" --symbols $$SYMS --venue "$(VENUE)" --max-workers "$(WORKERS)"

# -------- Catalog --------
.PHONY: db-init
db-init:
	@echo "[db] initializing catalog at $(CATALOG_DB)" && \
	mkdir -p $(dir $(CATALOG_DB)) && \
	echo "-- See docs/architecture.md: Catalog Schema (SQLite DDL)" && \
	echo "sqlite3 $(CATALOG_DB) < scripts/catalog_init.sql"

.PHONY: db-apply
db-apply:
	@mkdir -p $(dir $(CATALOG_DB)) && \
	test -f scripts/catalog_init.sql && \
	sqlite3 $(CATALOG_DB) < scripts/catalog_init.sql && \
	echo "[db] schema applied to $(CATALOG_DB)" || \
	(echo "[db] missing scripts/catalog_init.sql or sqlite3; see docs" && false)

# -------- Quality --------
.PHONY: lint
lint:
	@echo "[lint] backend (ruff)" && \
	test -d $(BACKEND_DIR) && $(PYTHON) ruff check $(BACKEND_DIR) || true ; \
	echo "[lint] bff (ruff)" && \
	test -d $(BFF_DIR) && $(PYTHON) ruff check $(BFF_DIR) || true ; \
	echo "[lint] frontend (eslint)" && \
	test -d $(FRONTEND_DIR) && (cd $(FRONTEND_DIR) && $(NPM) run lint) || true

.PHONY: format
format:
	@echo "[format] backend (black)" && \
	test -d $(BACKEND_DIR) && $(PYTHON) black $(BACKEND_DIR) || true ; \
	echo "[format] bff (black)" && \
	test -d $(BFF_DIR) && $(PYTHON) black $(BFF_DIR) || true ; \
	echo "[format] frontend (prettier)" && \
	test -d $(FRONTEND_DIR) && (cd $(FRONTEND_DIR) && $(NPM) run format) || true

.PHONY: test
test:
	@echo "[test] backend (pytest)" && \
	test -d $(BACKEND_DIR) && $(PYTHON) pytest -q || true ; \
	echo "[test] bff (pytest)" && \
	test -d $(BFF_DIR) && $(PYTHON) pytest $(BFF_DIR)/tests/ -q || true ; \
	echo "[test] frontend (vitest)" && \
	test -d $(FRONTEND_DIR) && (cd $(FRONTEND_DIR) && $(NPM) test -s) || true

# -------- Utility --------
.PHONY: env
env:
	@echo "[versions] Python:" && $(PYTHON) python --version || true ; \
	echo "[versions] uv:" && $(UV) --version || true ; \
	echo "[versions] Node:" && $(NODE) --version || true ; \
	echo "[versions] npm:" && $(NPM) --version || true

.PHONY: clean
clean:
	@echo "[clean] removing caches" && \
	rm -rf .pytest_cache __pycache__ */__pycache__ .ruff_cache || true



# -------- CI parity helpers --------
.PHONY: dev-install
dev-install:
	@echo "[dev-install] installing pinned toolchain (requirements-dev.txt)" && \
	$(UV) pip install -r requirements-dev.txt

.PHONY: ci-versions
ci-versions:
	@(.venv/bin/python -V || python3 -V || python -V) && \
	(.venv/bin/ruff --version || ruff --version) && \
	(.venv/bin/black --version || black --version) && \
	(.venv/bin/mypy --version || mypy --version) && \
	(.venv/bin/pytest --version || pytest --version) && \
	(.venv/bin/bandit --version || bandit --version) && \
	(.venv/bin/pip-audit --version || pip-audit --version) && \
	(.venv/bin/python -c "import importlinter, grimp; print('import-linter', getattr(importlinter, '__version__', 'unknown')); print('grimp', getattr(grimp, '__version__', 'unknown'))" || \
	 python3 -c "import importlinter, grimp; print('import-linter', getattr(importlinter, '__version__', 'unknown')); print('grimp', getattr(grimp, '__version__', 'unknown'))")

.PHONY: ci-architecture
ci-architecture:
	@echo "[ci-architecture] import-linter" && \
	$(PYTHON) lint-imports --config linter.ini

.PHONY: ci
ci:
	@echo "[ci] Using pinned toolchain — run: make setup && make dev-install (once)" && \
	$(MAKE) ci-versions && \
	echo "[ci] Ruff (lint)" && ( if [ -x .venv/bin/ruff ]; then .venv/bin/ruff check backend bff; else ruff check backend bff; fi ) && \
	echo "[ci] Black (format check)" && ( if [ -x .venv/bin/black ]; then .venv/bin/black --check backend bff; else black --check backend bff; fi ) && \
	echo "[ci] MyPy (type check)" && ( if [ -x .venv/bin/mypy ]; then .venv/bin/mypy backend bff; else mypy backend bff; fi ) && \
	echo "[ci] Import Linter (architecture)" && ( if [ -x .venv/bin/lint-imports ]; then .venv/bin/lint-imports --config linter.ini; else lint-imports --config linter.ini; fi ) && \
	echo "[ci] PyTest (backend)" && ( if [ -x .venv/bin/pytest ]; then PYTHONPATH=. .venv/bin/pytest -q backend/tests --cov=backend --cov-report=term-missing; else PYTHONPATH=. pytest -q backend/tests --cov=backend --cov-report=term-missing; fi ) && \
	echo "[ci] PyTest (bff)" && ( if [ -x .venv/bin/pytest ]; then PYTHONPATH=. .venv/bin/pytest -q bff/tests --cov=bff --cov-report=term-missing; else PYTHONPATH=. pytest -q bff/tests --cov=bff --cov-report=term-missing; fi ) && \
	echo "[ci] Bandit (security)" && ( if [ -x .venv/bin/bandit ]; then .venv/bin/bandit -q -r backend bff; else bandit -q -r backend bff; fi ) || true && \
	echo "[ci] pip-audit (dependencies)" && ( if [ -x .venv/bin/pip-audit ]; then .venv/bin/pip-audit --progress-spinner=off; else pip-audit --progress-spinner=off; fi ) || true && \
	echo "[ci] Frontend: Prettier check" && cd $(FRONTEND_DIR) && { export NVM_DIR="$$HOME/.nvm"; [ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh" && nvm use 22 >/dev/null 2>&1 || true; } && $(NPM) run prettier:check && \
	echo "[ci] Frontend: ESLint (components/containers/views)" && $(NPM) run lint && \
	echo "[ci] Frontend: ESLint (services/hooks/utils/store)" && $(NPM) run lint:services && \
	echo "[ci] Frontend: Type check" && $(NPM) run type-check && \
	echo "[ci] Frontend: Vitest (run once)" && $(NPM) test -s -- --run
