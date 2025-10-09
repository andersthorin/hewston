"""SQLite-backed implementation of CatalogPort for local/dev usage.

Provides minimal schema bootstrap and lightweight migrations suitable for tests.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import suppress
from datetime import UTC
from typing import Any

from backend.domain.models import BacktestSummary, Dataset
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

-- Canonical tables
CREATE TABLE IF NOT EXISTS backtests (
    backtest_id TEXT PRIMARY KEY,
    dataset_id TEXT REFERENCES datasets(dataset_id),
    strategy_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    duration_ms INTEGER,
    manifest_json TEXT,
    metrics_json TEXT,
    -- Optional extended columns (added in migrations when missing)
    params_json TEXT,
    seed INTEGER,
    slippage_fees_json TEXT,
    speed INTEGER,
    code_hash TEXT,
    metrics_path TEXT,
    equity_path TEXT,
    orders_path TEXT,
    fills_path TEXT,
    run_manifest_path TEXT,
    input_hash TEXT,
    idempotency_key TEXT
);

CREATE TABLE IF NOT EXISTS backtest_metrics (
    backtest_id TEXT PRIMARY KEY REFERENCES backtests(backtest_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    total_return REAL,
    max_drawdown REAL,
    computed_at TEXT NOT NULL
);


"""


class SqliteCatalog(CatalogPort):
    """SQLite-backed catalog for storing backtests, datasets, and metrics."""
    def __init__(self, db_path: str | None = None) -> None:
        """Initialize the catalog, creating directories and schema when needed.

        When db_path is ":memory:", a shared connection is used so schema persists
        across operations within the process.
        """
        resolved = db_path or os.getenv("HEWSTON_CATALOG_PATH", "data/catalog.db")
        self.db_path = resolved
        self._conn: sqlite3.Connection | None = None
        if resolved != ":memory:":
            dirn = os.path.dirname(resolved)
            if dirn:
                os.makedirs(dirn, exist_ok=True)
            self._bootstrap_if_missing()
            # Ensure newer columns/tables exist if DB was created with older minimal DDL
            self._migrate_schema()
        else:
            # Single shared in-memory connection so schema persists across operations
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            try:
                self._conn.execute("PRAGMA foreign_keys=ON;")
                self._conn.execute("PRAGMA busy_timeout=2000;")
            except Exception:
                pass
            # Initialize minimal schema in-memory for list/get operations in tests
            with self._conn:
                self._conn.executescript(DDL)
            self._migrate_schema()

    def _connect(self) -> sqlite3.Connection:
        if self.db_path == ":memory:" and self._conn is not None:
            return self._conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable FK, WAL and set a reasonable busy timeout to reduce lock contention
        with suppress(Exception):
            conn.execute("PRAGMA foreign_keys=ON;")
        with suppress(Exception):
            conn.execute("PRAGMA journal_mode=WAL;")
        with suppress(Exception):
            conn.execute("PRAGMA busy_timeout=2000;")  # 2 seconds
        return conn

    def _bootstrap_if_missing(self) -> None:
        """Create DB from official DDL if missing; fallback to minimal DDL.

        Does nothing if the file already exists to avoid schema divergence.
        """
        # Check BEFORE calling _connect() which creates the file
        db_exists = os.path.exists(self.db_path)

        # Try to apply repository DDL
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ddl_path = os.path.join(repo_root, "scripts", "catalog_init.sql")

        with self._connect() as conn:
            if not db_exists:
                # Fresh database - initialize schema
                if os.path.isfile(ddl_path):
                    with open(ddl_path) as f:
                        conn.executescript(f.read())
                else:
                    conn.executescript(DDL)

    def _migrate_schema(self) -> None:
        """Best-effort lightweight migration to ensure required columns/tables exist.

        Safe for dev/local testing. Adds missing columns with relaxed nullability.
        """
        with self._connect() as conn:
            # Helper to check column existence
            def col_exists(table: str, col: str) -> bool:
                rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
                return any(r[1] == col for r in rows)

            # datasets: ensure extended columns used by upsert_dataset
            if conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='datasets'"
            ).fetchone():
                for col, decl in [
                    ("products_json", "TEXT"),
                    ("calendar_version", "TEXT"),
                    ("tz", "TEXT"),
                    ("raw_dbn_json", "TEXT"),
                    ("bars_parquet_json", "TEXT"),
                    ("bars_manifest_path", "TEXT"),
                    ("generated_at", "TEXT"),
                    ("size_bytes", "INTEGER"),
                    ("status", "TEXT"),
                ]:
                    if not col_exists("datasets", col):
                        conn.execute(f"ALTER TABLE datasets ADD COLUMN {col} {decl}")

            # backtests: ensure columns used by create_run and set_run_status
            if conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='backtests'"
            ).fetchone():
                for col, decl in [
                    ("params_json", "TEXT"),
                    ("seed", "INTEGER"),
                    ("slippage_fees_json", "TEXT"),
                    ("speed", "INTEGER"),
                    ("code_hash", "TEXT"),
                    ("metrics_path", "TEXT"),
                    ("equity_path", "TEXT"),
                    ("orders_path", "TEXT"),
                    ("fills_path", "TEXT"),
                    ("run_manifest_path", "TEXT"),
                    ("input_hash", "TEXT"),
                    ("idempotency_key", "TEXT"),
                ]:
                    if not col_exists("backtests", col):
                        conn.execute(f"ALTER TABLE backtests ADD COLUMN {col} {decl}")

            # backtest_metrics: minimal table for metrics upsert
            conn.execute(
                "CREATE TABLE IF NOT EXISTS backtest_metrics (\n"
                "  backtest_id TEXT PRIMARY KEY REFERENCES backtests(backtest_id) "
                "ON UPDATE CASCADE ON DELETE CASCADE,\n"
                "  total_return REAL,\n"
                "  max_drawdown REAL,\n"
                "  computed_at TEXT NOT NULL\n"
                ")"
            )

            # No legacy views; canonical tables only

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(DDL)

    def get_backtest(self, run_id: str) -> dict[str, Any] | None:
        """Fetch a single backtest by ID; returns None if not found."""
        import json as _json

        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM backtests WHERE backtest_id = ?", (run_id,)
            ).fetchone()
            if not row:
                return None
            cols = row.keys() if hasattr(row, "keys") else []

            def _col(name: str):
                return row[name] if name in cols else None

            # Parse JSON columns safely
            def _parse(j):
                try:
                    return _json.loads(j) if j is not None else None
                except Exception:
                    return None

            run_manifest_path = _col("run_manifest_path")
            return {
                "run_id": row["backtest_id"],
                "dataset_id": row["dataset_id"],
                "strategy_id": row["strategy_id"],
                "params": _parse(_col("params_json")),
                "seed": _col("seed"),
                "slippage_fees": _parse(_col("slippage_fees_json")),
                "speed": _col("speed"),
                "code_hash": _col("code_hash"),
                "created_at": row["created_at"],
                "status": row["status"],
                "duration_ms": _col("duration_ms"),
                "artifacts": {
                    "metrics_path": _col("metrics_path"),
                    "equity_path": _col("equity_path"),
                    "orders_path": _col("orders_path"),
                    "fills_path": _col("fills_path"),
                    "run_manifest_path": run_manifest_path,
                },
                # Optional convenience link
                "manifest": {"path": run_manifest_path} if run_manifest_path else None,
            }

    def list_backtests(
        self,
        *,
        symbol: str | None = None,
        strategy_id: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 20,
        offset: int = 0,
        order: str = "-created_at",
    ) -> tuple[list[BacktestSummary], int]:
        """List backtests and total count with optional filters and pagination."""
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
            total = conn.execute(
                (
                    "SELECT COUNT(1) AS c FROM backtests b LEFT JOIN datasets d "
                    "ON d.dataset_id = b.dataset_id "
                    f"{where}"
                ),
                params,
            ).fetchone()["c"]
            q = (
                "SELECT b.backtest_id AS run_id, b.created_at, b.strategy_id, b.status, "
                "d.symbol AS symbol, b.duration_ms AS duration_ms "
                f"FROM backtests b LEFT JOIN datasets d ON d.dataset_id = b.dataset_id {where} "
                f"ORDER BY b.created_at {order_dir} LIMIT ? OFFSET ?"
            )
            rows = conn.execute(q, (*params, limit, offset)).fetchall()
            items = [
                BacktestSummary(
                    run_id=r["run_id"],
                    created_at=r["created_at"],
                    strategy_id=r["strategy_id"],
                    status=r["status"],
                    symbol=r["symbol"],
                    # run_from/run_to intentionally left None here to avoid cross-run bleed
                    # from dataset bounds
                    run_from=None,
                    run_to=None,
                    duration_ms=r["duration_ms"],
                )
                for r in rows
            ]
            return items, total

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        """Fetch a dataset by ID; returns None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,)
            ).fetchone()
            if not row:
                return None
            return Dataset(
                dataset_id=row["dataset_id"],
                symbol=row["symbol"],
                from_date=row["from_date"],
                to_date=row["to_date"],
            )

    # Stubs
    def upsert_dataset(self, dataset: dict[str, Any]) -> None:
        """Insert or update a dataset record (idempotent by dataset_id)."""
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
            (rec.get("bars_manifest_path") or ""),
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

    def create_backtest(
        self,
        *,
        run_id: str,
        dataset_id: str | None,  # Allow None - FK constraint allows NULL
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
        """Insert a new backtest row and return run_id."""
        with self._connect() as conn:
            conn.execute(
                (
                    "INSERT INTO backtests ("
                    "backtest_id, dataset_id, strategy_id, params_json, seed, "
                    "slippage_fees_json, speed, code_hash, created_at, status, "
                    "run_manifest_path, input_hash, idempotency_key) "
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

    def set_backtest_status(
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
        """Update backtest status and optional artifact paths/fields."""
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
            conn.execute(f"UPDATE backtests SET {', '.join(sets)} WHERE backtest_id = ?", params)

    def upsert_backtest_metrics(self, run_id: str, metrics: dict[str, Any]) -> None:
        """Insert or update metrics (maps win_rate -> hit_rate for schema)."""
        from datetime import datetime

        computed_at = datetime.now(UTC).isoformat()

        # Extract metrics (map win_rate to hit_rate for DB schema compatibility)
        total_return = metrics.get("total_return")
        max_drawdown = metrics.get("max_drawdown")
        hit_rate = metrics.get("win_rate")  # win_rate in code, hit_rate in DB

        with self._connect() as conn:
            conn.execute(
                (
                    "INSERT INTO backtest_metrics (backtest_id, total_return, max_drawdown, "
                    "hit_rate, computed_at) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(backtest_id) DO UPDATE SET "
                    "total_return=excluded.total_return, "
                    "max_drawdown=excluded.max_drawdown, "
                    "hit_rate=excluded.hit_rate, "
                    "computed_at=excluded.computed_at"
                ),
                (run_id, total_return, max_drawdown, hit_rate, computed_at),
            )

    def find_backtest_by_input_hash(self, input_hash: str) -> dict[str, Any] | None:
        """Find backtest by input hash; returns {'run_id': ...} or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT backtest_id FROM backtests WHERE input_hash = ?", (input_hash,)
            ).fetchone()
            if not row:
                return None
            return {"run_id": row["backtest_id"]}

    def find_backtest_by_idempotency_key(self, idem: str) -> dict[str, Any] | None:
        """Find backtest by idempotency key; returns {'run_id': ...} or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT backtest_id FROM backtests WHERE idempotency_key = ?", (idem,)
            ).fetchone()
            if not row:
                return None
            return {"run_id": row["backtest_id"]}
