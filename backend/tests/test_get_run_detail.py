"""Backtest detail REST shape tests with seeded SQLite catalog."""

import os
import sqlite3
import tempfile
from http import HTTPStatus

from fastapi.testclient import TestClient

import backend.services.backtests as svc
from backend.adapters.sqlite_catalog import SqliteCatalog
from backend.app.main import app

EXPECTED_SEED = 42
EXPECTED_SPEED = 60
EXPECTED_DURATION_MS = 1234


def seed_one_run(db_path: str):
    """Seed minimal dataset and backtest rows into a sqlite catalog."""
    SqliteCatalog(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute(
            """
            INSERT INTO datasets (dataset_id, symbol, from_date, to_date, products_json,
                                  calendar_version, tz,
                                  raw_dbn_json, bars_parquet_json,
                                  bars_manifest_path, generated_at, size_bytes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ds1",
                "AAPL",
                "2023-01-01",
                "2024-12-31",
                "[]",
                "v1",
                "UTC",
                "[]",
                "[]",
                "/tmp/bars1.manifest",
                "2024-01-01T00:00:00Z",
                0,
                "READY",
            ),
        )
        conn.execute(
            """
            INSERT INTO backtests (backtest_id, dataset_id, strategy_id, params_json,
                                  seed, slippage_fees_json, speed,
                                  code_hash, created_at, status, duration_ms,
                                  metrics_path, equity_path,
                                  orders_path,
                                  fills_path, run_manifest_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "r100",
                "ds1",
                "sma_crossover",
                '{"fast":10,"slow":20}',
                42,
                '{"fee":0.0}',
                60,
                "abcd",
                "2024-07-01T12:00:00Z",
                "DONE",
                1234,
                "/tmp/metrics.json",
                "/tmp/equity.json",
                "/tmp/orders.json",
                "/tmp/fills.json",
                "/tmp/run.manifest",
            ),
        )


def test_get_run_detail_shape(monkeypatch):
    """Validate detail shape contains core fields and artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "catalog.db")
        seed_one_run(db_path)
        monkeypatch.setattr(svc, "get_catalog", lambda: SqliteCatalog(db_path))

        client = TestClient(app)
        r = client.get("/api/v1/backtests/r100")
        assert r.status_code == HTTPStatus.OK
        j = r.json()
        # Core fields
        assert j["run_id"] == "r100"
        assert j["dataset_id"] == "ds1"
        assert j["strategy_id"] == "sma_crossover"
        assert j["status"] == "DONE"
        assert j["code_hash"] == "abcd"
        assert j["seed"] == EXPECTED_SEED
        assert j["speed"] == EXPECTED_SPEED
        assert j["duration_ms"] == EXPECTED_DURATION_MS
        assert isinstance(j["params"], dict)
        assert isinstance(j["slippage_fees"], dict)
        # Artifacts object
        a = j["artifacts"]
        assert a["metrics_path"].endswith("metrics.json")
        assert a["equity_path"].endswith("equity.json")
        assert a["orders_path"].endswith("orders.json")
        assert a["fills_path"].endswith("fills.json")
        assert a["run_manifest_path"].endswith("run.manifest")
        # Optional manifest link
        assert j["manifest"]["path"].endswith("run.manifest")
