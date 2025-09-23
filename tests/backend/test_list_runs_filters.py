import os
import tempfile
import sqlite3
from datetime import datetime

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.adapters.sqlite_catalog import SqliteCatalog
import backend.services.backtests as svc


def seed_sample_db(db_path: str):
    cat = SqliteCatalog(db_path)
    with sqlite3.connect(db_path) as conn:
        # Ensure foreign keys
        conn.execute("PRAGMA foreign_keys=ON;")
        # Insert datasets
        conn.execute(
            """
            INSERT INTO datasets (dataset_id, symbol, from_date, to_date, products_json, calendar_version, tz,
                                  raw_dbn_json, bars_parquet_json, bars_manifest_path, generated_at, size_bytes, status)
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
            INSERT INTO datasets (dataset_id, symbol, from_date, to_date, products_json, calendar_version, tz,
                                  raw_dbn_json, bars_parquet_json, bars_manifest_path, generated_at, size_bytes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ds2",
                "MSFT",
                "2023-01-01",
                "2024-12-31",
                "[]",
                "v1",
                "UTC",
                "[]",
                "[]",
                "/tmp/bars2.manifest",
                "2024-01-01T00:00:00Z",
                0,
                "READY",
            ),
        )
        # Insert runs
        conn.execute(
            """
            INSERT INTO runs (run_id, dataset_id, strategy_id, params_json, seed, slippage_fees_json, speed,
                              code_hash, created_at, status, duration_ms, metrics_path, equity_path, orders_path,
                              fills_path, run_manifest_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "r1",
                "ds1",
                "sma_crossover",
                "{}",
                42,
                "{}",
                60,
                "hash1",
                "2024-01-01T00:00:00Z",
                "DONE",
                1000,
                None,
                None,
                None,
                None,
                "/tmp/run1.manifest",
            ),
        )
        conn.execute(
            """
            INSERT INTO runs (run_id, dataset_id, strategy_id, params_json, seed, slippage_fees_json, speed,
                              code_hash, created_at, status, duration_ms, metrics_path, equity_path, orders_path,
                              fills_path, run_manifest_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "r2",
                "ds1",
                "momentum",
                "{}",
                42,
                "{}",
                60,
                "hash2",
                "2024-06-01T00:00:00Z",
                "DONE",
                1500,
                None,
                None,
                None,
                None,
                "/tmp/run2.manifest",
            ),
        )
        conn.execute(
            """
            INSERT INTO runs (run_id, dataset_id, strategy_id, params_json, seed, slippage_fees_json, speed,
                              code_hash, created_at, status, duration_ms, metrics_path, equity_path, orders_path,
                              fills_path, run_manifest_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "r3",
                "ds2",
                "sma_crossover",
                "{}",
                42,
                "{}",
                60,
                "hash3",
                "2024-03-01T00:00:00Z",
                "DONE",
                900,
                None,
                None,
                None,
                None,
                "/tmp/run3.manifest",
            ),
        )


def test_list_runs_filters_and_order(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "catalog.sqlite")
        seed_sample_db(db_path)
        # Force services to use our temp DB
        monkeypatch.setattr(svc, "get_catalog", lambda: SqliteCatalog(db_path))

        client = TestClient(app)

        # Default order: -created_at (DESC)
        r = client.get("/backtests", params={"symbol": "AAPL"})
        assert r.status_code == 200
        j = r.json()
        assert [it["run_id"] for it in j["items"]] == ["r2", "r1"]
        assert j["total"] >= 2
        assert "from" in j["items"][0] and "to" in j["items"][0]

        # ASC order
        r2 = client.get("/backtests", params={"symbol": "AAPL", "order": "created_at"})
        assert r2.status_code == 200
        j2 = r2.json()
        assert [it["run_id"] for it in j2["items"]] == ["r1", "r2"]

        # strategy_id filter
        r3 = client.get("/backtests", params={"strategy_id": "sma_crossover"})
        j3 = r3.json()
        assert {it["run_id"] for it in j3["items"]} == {"r1", "r3"}

        # from/to overlap filter (dataset to_date >= from and from_date <= to)
        r4 = client.get("/backtests", params={"from": "2024-05-01", "to": "2024-06-30"})
        j4 = r4.json()
        # Both datasets cover 2024, so all runs shown
        assert {it["run_id"] for it in j4["items"]} == {"r1", "r2", "r3"}

        # Clamp limit to 500
        r5 = client.get("/backtests", params={"limit": 1000})
        j5 = r5.json()
        assert j5["limit"] == 500

