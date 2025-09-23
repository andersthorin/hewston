from __future__ import annotations

import os
import sqlite3
from typing import Optional, List, Tuple, Dict, Any

from backend.domain.models import RunSummary, Dataset
from backend.ports.catalog import CatalogPort

DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    from_date TEXT,
    to_date TEXT,
    manifest_json TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    dataset_id TEXT REFERENCES datasets(dataset_id),
    strategy_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    duration_ms INTEGER,
    manifest_json TEXT,
    metrics_json TEXT
);

CREATE VIEW IF NOT EXISTS runs_list AS
SELECT r.run_id,
       r.created_at,
       r.strategy_id,
       r.status,
       d.symbol AS symbol,
       d.from_date AS from_date,
       d.to_date AS to_date,
       r.duration_ms AS duration_ms
FROM runs r
LEFT JOIN datasets d ON d.dataset_id = r.dataset_id;
"""


class SqliteCatalog(CatalogPort):
    def __init__(self, db_path: str | None = None) -> None:
        resolved = db_path or os.getenv("HEWSTON_CATALOG_PATH", "data/catalog.sqlite")
        self.db_path = resolved
        if resolved != ":memory:":
            dirn = os.path.dirname(resolved)
            if dirn:
                os.makedirs(dirn, exist_ok=True)
            self._bootstrap_if_missing()
        else:
            # Initialize minimal schema in-memory for list/get operations in tests
            self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _bootstrap_if_missing(self) -> None:
        """Create DB from official DDL if missing; fallback to minimal DDL.
        Does nothing if the file already exists to avoid schema divergence.
        """
        if os.path.exists(self.db_path):
            return
        # Try to apply repository DDL
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ddl_path = os.path.join(repo_root, "scripts", "catalog_init.sql")
        with self._connect() as conn:
            if os.path.isfile(ddl_path):
                with open(ddl_path, "r") as f:
                    conn.executescript(f.read())
            else:
                conn.executescript(DDL)


    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(DDL)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        import json as _json
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if not row:
                return None
            # Parse JSON columns safely
            def _parse(j):
                try:
                    return _json.loads(j) if j is not None else None
                except Exception:
                    return None
            return {
                "run_id": row["run_id"],
                "dataset_id": row["dataset_id"],
                "strategy_id": row["strategy_id"],
                "params": _parse(row["params_json"]),
                "seed": row["seed"],
                "slippage_fees": _parse(row["slippage_fees_json"]),
                "speed": row["speed"],
                "code_hash": row["code_hash"],
                "created_at": row["created_at"],
                "status": row["status"],
                "duration_ms": row["duration_ms"],
                "artifacts": {
                    "metrics_path": row["metrics_path"],
                    "equity_path": row["equity_path"],
                    "orders_path": row["orders_path"],
                    "fills_path": row["fills_path"],
                    "run_manifest_path": row["run_manifest_path"],
                },
                # Optional convenience link
                "manifest": {"path": row["run_manifest_path"]} if row["run_manifest_path"] else None,
            }

    def list_runs(
        self,
        *,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        order: str = "-created_at",
    ) -> tuple[List[RunSummary], int]:
        clauses = []
        params: list = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol)
        if strategy_id:
            clauses.append("strategy_id = ?")
            params.append(strategy_id)
        # Overlap semantics
        if from_date:
            clauses.append("to_date >= ?")
            params.append(from_date)
        if to_date:
            clauses.append("from_date <= ?")
            params.append(to_date)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        order_dir = "DESC" if str(order).strip().startswith("-") else "ASC"

        with self._connect() as conn:
            total = conn.execute(f"SELECT COUNT(1) AS c FROM runs_list {where}", params).fetchone()["c"]
            q = (
                f"SELECT run_id, created_at, strategy_id, status, symbol, from_date, to_date, duration_ms "
                f"FROM runs_list {where} ORDER BY created_at {order_dir} LIMIT ? OFFSET ?"
            )
            rows = conn.execute(q, (*params, limit, offset)).fetchall()
            items = [
                RunSummary(
                    run_id=r["run_id"],
                    created_at=r["created_at"],
                    strategy_id=r["strategy_id"],
                    status=r["status"],
                    symbol=r["symbol"],
                    from_date=r["from_date"],
                    to_date=r["to_date"],
                    duration_ms=r["duration_ms"],
                )
                for r in rows
            ]
            return items, total

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,)).fetchone()
            if not row:
                return None
            return Dataset(
                dataset_id=row["dataset_id"],
                symbol=row["symbol"],
                from_date=row["from_date"],
                to_date=row["to_date"],
            )

    # Stubs
    def upsert_dataset(self, dataset: Dict[str, Any]) -> None:
        import json as _json
        rec = dict(dataset)
        # Ensure JSON TEXT fields are serialized deterministically
        def dumps(o):
            return _json.dumps(o, sort_keys=True)
        rec["products_json"] = dumps(rec.get("products", []))
        rec["raw_dbn_json"] = dumps(rec.get("raw_dbn", []))
        rec["bars_parquet_json"] = dumps(rec.get("bars_parquet", []))
        cols = (
            "dataset_id,symbol,from_date,to_date,products_json,calendar_version,tz,"
            "raw_dbn_json,bars_parquet_json,bars_manifest_path,generated_at,size_bytes,status"
        )
        placeholders = ",".join(["?"] * 13)
        values = [
            rec["dataset_id"],
            rec["symbol"],
            rec["from_date"],
            rec["to_date"],
            rec["products_json"],
            rec.get("calendar_version", "v1"),
            rec.get("tz", "America/New_York"),
            rec["raw_dbn_json"],
            rec["bars_parquet_json"],
            rec["bars_manifest_path"],
            rec["generated_at"],
            int(rec.get("size_bytes", 0)),
            rec.get("status", "READY"),
        ]
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO datasets ({cols}) VALUES ({placeholders})\n"
                "ON CONFLICT(dataset_id) DO UPDATE SET\n"
                "  symbol=excluded.symbol,\n"
                "  from_date=excluded.from_date,\n"
                "  to_date=excluded.to_date,\n"
                "  products_json=excluded.products_json,\n"
                "  calendar_version=excluded.calendar_version,\n"
                "  tz=excluded.tz,\n"
                "  raw_dbn_json=excluded.raw_dbn_json,\n"
                "  bars_parquet_json=excluded.bars_parquet_json,\n"
                "  bars_manifest_path=excluded.bars_manifest_path,\n"
                "  generated_at=excluded.generated_at,\n"
                "  size_bytes=excluded.size_bytes,\n"
                "  status=excluded.status",
                values,
            )


    def create_run(
        self,
        *,
        run_id: str,
        dataset_id: str,
        strategy_id: str,
        params_json: str,
        seed: int,
        slippage_fees_json: str,
        speed: int,
        code_hash: str,
        created_at: str,
        status: str,
        run_manifest_path: str,
        input_hash: str | None,
        idempotency_key: str | None,
    ) -> str:
        with self._connect() as conn:
            conn.execute(
                (
                    "INSERT INTO runs (run_id, dataset_id, strategy_id, params_json, seed, slippage_fees_json, speed, "
                    "code_hash, created_at, status, run_manifest_path, input_hash, idempotency_key) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                (
                    run_id,
                    dataset_id,
                    strategy_id,
                    params_json,
                    seed,
                    slippage_fees_json,
                    speed,
                    code_hash,
                    created_at,
                    status,
                    run_manifest_path,
                    input_hash,
                    idempotency_key,
                ),
            )
        return run_id

    def set_run_status(
        self,
        run_id: str,
        *,
        status: str,
        duration_ms: int | None = None,
        metrics_path: str | None = None,
        equity_path: str | None = None,
        orders_path: str | None = None,
        fills_path: str | None = None,
    ) -> None:
        sets = ["status = ?"]
        params: list = [status]
        if duration_ms is not None:
            sets.append("duration_ms = ?")
            params.append(int(duration_ms))
        if metrics_path is not None:
            sets.append("metrics_path = ?")
            params.append(metrics_path)
        if equity_path is not None:
            sets.append("equity_path = ?")
            params.append(equity_path)
        if orders_path is not None:
            sets.append("orders_path = ?")
            params.append(orders_path)
        if fills_path is not None:
            sets.append("fills_path = ?")
            params.append(fills_path)
        params.append(run_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE runs SET {', '.join(sets)} WHERE run_id = ?", params)

    def upsert_run_metrics(self, run_id: str, metrics: Dict[str, Any]) -> None:
        from datetime import datetime, timezone

        computed_at = datetime.now(timezone.utc).isoformat()
        # Minimal set: total_return and max_drawdown; others NULL
        total_return = metrics.get("total_return")
        max_drawdown = metrics.get("max_drawdown")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO run_metrics (run_id, total_return, max_drawdown, computed_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET total_return=excluded.total_return, max_drawdown=excluded.max_drawdown, computed_at=excluded.computed_at",
                (run_id, total_return, max_drawdown, computed_at),
            )


    def find_run_by_input_hash(self, input_hash: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE input_hash = ?", (input_hash,)).fetchone()
            return dict(row) if row else None

    def find_run_by_idempotency_key(self, idem: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE idempotency_key = ?", (idem,)).fetchone()
            return dict(row) if row else None
