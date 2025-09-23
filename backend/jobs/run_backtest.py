from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import polars as pl

from backend.adapters.nautilus import NautilusBacktestRunner
from backend.adapters.sqlite_catalog import SqliteCatalog


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _code_hash() -> str:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, check=True, text=True
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _base_data_dir() -> Path:
    return Path(os.environ.get("HEWSTON_DATA_DIR", "data"))


def _write_parquet(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(records)
    df.write_parquet(path)


def run_backtest_and_persist(
    *,
    dataset_id: str,
    strategy_id: str = "sma_crossover",
    params: Dict[str, Any] | None = None,
    seed: int = 42,
    speed: int = 60,
    slippage_fees: Dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict:
    params = params or {}
    slippage_fees = slippage_fees or {}
    cat = SqliteCatalog()

    created_at = _utc_now()
    code_hash = _code_hash()

    # If run_id not supplied, create a new row (QUEUED)
    if not run_id:
        run_id = uuid.uuid4().hex
        # Prepare manifest path for DB row
        manifest_path_tmp = _base_data_dir() / "backtests" / run_id / "run-manifest.json"
        cat.create_run(
            run_id=run_id,
            dataset_id=dataset_id,
            strategy_id=strategy_id,
            params_json=json.dumps(params, sort_keys=True),
            seed=seed,
            slippage_fees_json=json.dumps(slippage_fees, sort_keys=True),
            speed=speed,
            code_hash=code_hash,
            created_at=created_at,
            status="QUEUED",
            run_manifest_path=str(manifest_path_tmp),
            input_hash=None,
            idempotency_key=None,
        )

    # Prepare paths
    out_dir = _base_data_dir() / "backtests" / run_id
    equity_path = out_dir / "equity.parquet"
    orders_path = out_dir / "orders.parquet"
    fills_path = out_dir / "fills.parquet"
    metrics_path = out_dir / "metrics.json"
    manifest_path = out_dir / "run-manifest.json"

    # Move to RUNNING
    cat.set_run_status(run_id, status="RUNNING")

    t0 = time.perf_counter()
    try:
        runner = NautilusBacktestRunner()
        result = runner.run(
            dataset_id=dataset_id, strategy_id=strategy_id, params=params, seed=seed
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)

        # Write artifacts
        _write_parquet(result.get("equity", []), equity_path)
        _write_parquet(result.get("orders", []), orders_path)
        _write_parquet(result.get("fills", []), fills_path)
        metrics = result.get("metrics", {})
        out_dir.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(metrics, indent=2))

        # Write manifest
        manifest = {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "strategy_id": strategy_id,
            "params": params,
            "seed": seed,
            "slippage_fees": slippage_fees,
            "speed": speed,
            "code_hash": code_hash,
            "env_lock": None,
            "calendar_version": "NAZDAQ-v1",
            "tz": "America/New_York",
            "created_at": created_at,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # Finalize DB row to DONE + metrics table
        cat.set_run_status(
            run_id,
            status="DONE",
            duration_ms=duration_ms,
            metrics_path=str(metrics_path),
            equity_path=str(equity_path),
            orders_path=str(orders_path),
            fills_path=str(fills_path),
        )
        cat.upsert_run_metrics(run_id, metrics)

        return {
            "run_id": run_id,
            "duration_ms": duration_ms,
            "paths": {
                "metrics": str(metrics_path),
                "equity": str(equity_path),
                "orders": str(orders_path),
                "fills": str(fills_path),
                "manifest": str(manifest_path),
            },
        }
    except Exception as e:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        cat.set_run_status(run_id, status="ERROR", duration_ms=duration_ms)
        try:
            import logging
            logging.getLogger(__name__).error(
                "run.error",
                extra={"run_id": run_id, "duration_ms": duration_ms, "code": "RUNNER_ERROR", "message": str(e)[:200]},
            )
        except Exception:
            pass
        raise

