# One command: make all
# Uses PostgreSQL by default (DATABASE_URL). Without Postgres: make all DB_ENGINE=duckdb
PYTHON ?= python3
VENV   := .venv
PY     := $(VENV)/bin/python
DB_ENGINE ?= postgres
export DB_ENGINE

.PHONY: all setup data load analysis charts powerbi dashboard test sample clean

all: setup data load analysis charts powerbi dashboard test

$(PY): requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --quiet -r requirements.txt
	@touch $(PY)

setup: $(PY)

data: setup
	$(PY) scripts/download_data.py

load: setup
	$(PY) -m dropoff.load

analysis: setup
	$(PY) -m dropoff.analysis

charts: setup
	$(PY) -m dropoff.charts

powerbi: setup
	$(PY) -m dropoff.powerbi

dashboard: setup
	$(PY) -m dropoff.dashboard

test: setup
	$(PY) -m pytest -q

# Offline run on the small committed sample, with DuckDB. Writes to build/sample/.
sample: export DB_ENGINE = duckdb
sample: export DATA_DIR = data/sample
sample: export OUT_DIR = build/sample
sample: export DOCS_DIR = build/sample/docs
sample: export DUCKDB_PATH = build/sample.duckdb
sample: setup
	mkdir -p build
	$(PY) -m dropoff.load
	$(PY) -m dropoff.analysis
	$(PY) -m dropoff.charts
	$(PY) -m dropoff.powerbi
	$(PY) -m dropoff.dashboard

clean:
	rm -rf build data/oulad.duckdb .pytest_cache
