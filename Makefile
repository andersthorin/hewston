.DEFAULT_GOAL := help

# -------- Variables --------
PYTHON := uv run
UV := uv
NODE := node
NPM := npm
BACKEND_DIR := backend
FRONTEND_DIR := frontend
CATALOG_DB := data/catalog.sqlite
# default envs for local dev (override as needed)
DATABENTO_API_KEY ?= test-key
HEWSTON_CATALOG_PATH ?= data/catalog.sqlite
HEWSTON_DATA_DIR ?= data

# Defaults (override on CLI: make data SYMBOL=AAPL YEAR=2023)
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

# -------- Meta --------
.PHONY: help
help:
	@echo "Hewston Make targets"
	@echo "  setup           Create Python venv (uv), prepare frontend (npm)"
	@echo "  start           Start backend API and frontend dev server (if present)"
	@echo "  start-backend   Start FastAPI dev server (uvicorn)"
	@echo "  start-frontend  Start Vite dev server"
		@echo "  stop            Stop backend and frontend dev servers"
		@echo "  restart        Restart backend and frontend (stop→start)"
		@echo "  derive-bars     Derive 1m bars from local DBN (SYMBOLS=... FROM=YYYY-MM-DD TO=YYYY-MM-DD FORCE=1)"

			@echo "  derive-daily    Derive 1d bars (daily OHLCV) from local DBN (SYMBOLS=... FROM=YYYY-MM-DD TO=YYYY-MM-DD FORCE=1)"
			@echo "  derive-daily-fast Derive 1d OHLCV from existing 1m parquet (fast path)"



	@echo "  data            Ingest Databento DBN and derive 1m bars (SYMBOL, YEAR)"
	@echo "  backtest        Run baseline backtest and write artifacts"
	@echo "  db-init         Initialize SQLite catalog (see docs/architecture.md)"
	@echo "  db-apply       Apply SQLite schema to $(CATALOG_DB)"

	@echo "  lint            Run linters (ruff/eslint)"
	@echo "  format          Run formatters (black/prettier)"
	@echo "  test            Run tests (pytest/vitest)"
	@echo "  env             Print tool versions"
	@echo "  clean           Remove caches and temp files"

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
	@echo "[stop] stopping servers on ports 8000, 5173-5174" && \
	pids=`lsof -nP -iTCP:8000,5173-5174 -sTCP:LISTEN -t 2>/dev/null || true`; \
	if [ -n "$$pids" ]; then \
	  echo "[stop] killing $$pids"; \
	  kill $$pids 2>/dev/null || true; \
	  sleep 0.5; \
	  pids2=`lsof -nP -iTCP:8000,5173-5174 -sTCP:LISTEN -t 2>/dev/null || true`; \
	  if [ -n "$$pids2" ]; then echo "[stop] force killing $$pids2"; kill -9 $$pids2 2>/dev/null || true; fi; \
	else \
	  echo "[stop] no listeners found"; \
	fi

.PHONY: restart
restart:
	@$(MAKE) stop
	@$(MAKE) -j2 start-backend start-frontend

start:
	@$(MAKE) -j2 start-backend start-frontend

.PHONY: start-backend
start-backend:
	@test -d $(BACKEND_DIR) && \
	  (echo "[backend] starting uvicorn" && \
	   DATABENTO_API_KEY=$(DATABENTO_API_KEY) HEWSTON_CATALOG_PATH=$(HEWSTON_CATALOG_PATH) HEWSTON_DATA_DIR=$(HEWSTON_DATA_DIR) \
	   $(PYTHON) uvicorn $(BACKEND_DIR).app.main:app --reload --host 127.0.0.1 --port 8000) \
	|| (echo "[backend] missing $(BACKEND_DIR)/ — scaffold later" && true)

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

.PHONY: derive-bars
derive-bars:
	@echo "[derive-bars] SYMBOLS=$(SYMBOLS) FROM=$(FROM) TO=$(TO) FORCE=$(FORCE)" && \
	HEWSTON_DATA_DIR="$(HEWSTON_DATA_DIR)" SYMBOLS="$(SYMBOLS)" FROM="$(FROM)" TO="$(TO)" FORCE="$(FORCE)" TF="$(TF)" FORMAT="$(FORMAT)" FILL_GAPS="$(FILL_GAPS)" RTH_ONLY="$(RTH_ONLY)" PYTHONWARNINGS=ignore \
	  python3 -W ignore:::urllib3.exceptions.NotOpenSSLWarning scripts/derive_bars_runner.py
.PHONY: derive-daily
derive-daily:
	@echo "[derive-daily] SYMBOLS=$(SYMBOLS) FROM=$(FROM) TO=$(TO) FORCE=$(FORCE)" && \
	HEWSTON_DATA_DIR="$(HEWSTON_DATA_DIR)" SYMBOLS="$(SYMBOLS)" FROM="$(FROM)" TO="$(TO)" FORCE="$(FORCE)" TF="1Day" FORMAT="$(FORMAT)" FILL_GAPS="0" RTH_ONLY="1" PYTHONWARNINGS=ignore \
	  python3 -W ignore:::urllib3.exceptions.NotOpenSSLWarning scripts/derive_bars_runner.py

.PHONY: derive-daily-fast
derive-daily-fast:
	@echo "[derive-daily-fast] SYMBOLS=$(SYMBOLS) FROM=$(FROM) TO=$(TO) FORCE=$(FORCE)" && \
	HEWSTON_DATA_DIR="$(HEWSTON_DATA_DIR)" SYMBOLS="$(SYMBOLS)" FROM="$(FROM)" TO="$(TO)" FORCE="$(FORCE)" FORMAT="parquet" RTH_ONLY="1" FILL_GAPS="0" \
	  python3 scripts/derive_daily_from_minute.py


.PHONY: derive-bars-legacy
derive-bars-legacy:
	@echo "[derive-bars] SYMBOLS=$(SYMBOLS) FROM=$(FROM) TO=$(TO) FORCE=$(FORCE)" && \
	SYMS_LIST=$$(python3 - <<'PY'
	import os,json
	sy=os.environ.get('SYMBOLS','ALL')
	if sy and sy.strip().upper()!='ALL':
	  syms=[s.strip() for s in sy.replace(',', ' ').split() if s.strip()]
	else:
	  import pathlib
	  base=pathlib.Path(os.environ.get('HEWSTON_DATA_DIR','data'))/'raw'/'databento'
	  p=base/'trades'/'symbology.json'
	  if not p.exists():
	    p=base/'tbbo'/'symbology.json'
	  syms=[]
	  try:
	    d=json.loads(p.read_text())
	    syms=list(d.get('result',{}).keys())
	  except Exception:
	    pass
	print(' '.join(syms))
	PY
	) && \
	YEARS_LIST=$$(python3 - <<'PY'
	import os,re,glob,pathlib
	fr=os.environ.get('FROM',''); to=os.environ.get('TO','')
	ys=set()
	if fr and to:
	  y1=int(fr[:4]); y2=int(to[:4]); ys.update(range(y1,y2+1))
	else:
	  base=pathlib.Path(os.environ.get('HEWSTON_DATA_DIR','data'))/'raw'/'databento'/'trades'
	  for p in glob.glob(str(base/'*.trades.dbn.zst')):
	    m=re.search(r'-(\d{8})\.trades\.dbn', p)
	    if m: ys.add(int(m.group(1)[:4]))
	print(' '.join(str(y) for y in sorted(ys)))
	PY
	) && \
	for s in $$SYMS_LIST; do \
	  for y in $$YEARS_LIST; do \
	    echo "[derive] $$s $$y FROM=$(FROM) TO=$(TO)"; \
	    $(PYTHON) -m backend.jobs.cli derive-bars --symbol $$s --year $$y $(if $(FROM),--from $(FROM),) $(if $(TO),--to $(TO),) $(if $(FORCE),--force,); \
	  done; \
	done

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
	echo "[lint] frontend (eslint)" && \
	test -d $(FRONTEND_DIR) && (cd $(FRONTEND_DIR) && $(NPM) run lint) || true

.PHONY: format
format:
	@echo "[format] backend (black)" && \
	test -d $(BACKEND_DIR) && $(PYTHON) black $(BACKEND_DIR) || true ; \
	echo "[format] frontend (prettier)" && \
	test -d $(FRONTEND_DIR) && (cd $(FRONTEND_DIR) && $(NPM) run format) || true

.PHONY: test
test:
	@echo "[test] backend (pytest)" && \
	test -d $(BACKEND_DIR) && $(PYTHON) pytest -q || true ; \
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

