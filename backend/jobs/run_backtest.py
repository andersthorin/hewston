from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict

import polars as pl

from backend.adapters.nautilus import NautilusBacktestRunner
from backend.utils.metrics import compute_cumulative_metrics
from backend.adapters.sqlite_catalog import SqliteCatalog
from backend.services.backtests import get_catalog
from backend.utils.datetime import utc_now
from backend.utils.git import get_git_commit_hash
from backend.utils.paths import get_base_data_dir, get_backtests_dir, ensure_dir

# Configure logging for backtest execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def _write_parquet(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(records)
    df.write_parquet(path)


def run_backtest_and_persist(
    *,
    dataset_id: str | None = None,  # Optional - not needed for warehouse-based backtests
    strategy_id: str = "sma_crossover",
    params: Dict[str, Any] | None = None,
    seed: int = 42,
    speed: int = 60,
    slippage_fees: Dict[str, Any] | None = None,
    run_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    logger = logging.getLogger("backtest.job")
    params = params or {}
    slippage_fees = slippage_fees or {}
    cat = get_catalog()

    logger.info(
        f"Starting backtest: dataset={dataset_id}, strategy={strategy_id}, "
        f"params={params}, from={from_date}, to={to_date}"
    )

    created_at_iso = utc_now().isoformat()
    code_hash = get_git_commit_hash() or "unknown"

    # If run_id not supplied, create a new row (QUEUED)
    if not run_id:
        run_id = uuid.uuid4().hex
        # Prepare manifest path for DB row
        manifest_path_tmp = get_backtests_dir(run_id) / "run-manifest.json"
        cat.create_backtest(
            run_id=run_id,
            dataset_id=dataset_id,
            strategy_id=strategy_id,
            params_json=json.dumps(params, sort_keys=True),
            seed=seed,
            slippage_fees_json=json.dumps(slippage_fees, sort_keys=True),
            speed=speed,
            code_hash=code_hash,
            created_at=created_at_iso,
            status="QUEUED",
            run_manifest_path=str(manifest_path_tmp),
            input_hash=None,
            idempotency_key=None,
        )

    # Prepare paths (absolute)
    out_dir = get_backtests_dir(run_id)
    out_dir_abs = out_dir.resolve()
    ensure_dir(out_dir_abs)
    equity_path = (out_dir_abs / "equity.parquet")
    orders_path = (out_dir_abs / "orders.parquet")
    fills_path = (out_dir_abs / "fills.parquet")
    metrics_path = (out_dir_abs / "metrics.json")
    manifest_path = (out_dir_abs / "run-manifest.json")

    # Move to RUNNING
    cat.set_backtest_status(run_id, status="RUNNING")

    # Do NOT prepare or derive datasets here; admin-only via CLI/APIs.
    # If dataset is missing/not-ready, the runner will raise and we record ERROR.

    t0 = time.perf_counter()
    try:
        logger.info("Initializing Nautilus backtest runner...")
        runner = NautilusBacktestRunner()

        logger.info("Running backtest...")
        result = runner.run(
            dataset_id=dataset_id, strategy_id=strategy_id, params=params, seed=seed,
            from_date=from_date, to_date=to_date,
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)

        # Log result summary
        logger.info(
            f"Backtest completed in {duration_ms}ms: "
            f"{len(result.get('orders', []))} orders, "
            f"{len(result.get('fills', []))} fills, "
            f"{len(result.get('equity', []))} equity points"
        )
        logger.info(f"Metrics: {result.get('metrics', {})}")

        # Write artifacts
        logger.info("Writing artifacts to disk...")
        _write_parquet(result.get("equity", []), equity_path)
        _write_parquet(result.get("orders", []), orders_path)
        _write_parquet(result.get("fills", []), fills_path)
        # Build metrics artifact: precompute cumulative series aligned to equity timestamps
        nautilus = result.get("nautilus", {}) or {}
        realized = []
        try:
            rp = (nautilus.get("series") or {}).get("realized_pnl") or []
            # Expect [[iso,value], ...]
            realized = [(str(a[0]), float(a[1])) for a in rp if isinstance(a, (list, tuple)) and len(a) >= 2]
        except Exception:
            realized = []

        # Fallback: derive cumulative realized PnL from fills when Nautilus analyzer series is missing
        if not realized:
            try:
                fills = result.get("fills", []) or []
                # Accumulate position and cost; compute realized on SELLs (netting semantics)
                pos_qty = 0
                avg_cost = 0.0
                realized_cum = 0.0
                realized_pairs: list[tuple[str, float]] = []
                from backend.utils.datetime import normalize_timestamp
                for f in fills:
                    qty = int(f.get("qty") or f.get("quantity") or 0)
                    px = float(f.get("price") or 0.0)
                    side = str(f.get("side") or "").upper()
                    ts_raw = f.get("ts_utc") or f.get("timestamp") or f.get("ts")
                    # Normalize ts to ISO (best-effort)
                    try:
                        _, ts_iso = normalize_timestamp(ts_raw)
                    except Exception:
                        ts_iso = str(ts_raw) if ts_raw is not None else None
                    if side == "BUY":
                        # Update weighted average cost
                        new_qty = pos_qty + qty
                        if new_qty > 0:
                            avg_cost = ((avg_cost * pos_qty) + (px * qty)) / float(new_qty)
                        pos_qty = new_qty
                    elif side == "SELL":
                        # Realize PnL for the quantity sold
                        realized_cum += (px - avg_cost) * qty
                        pos_qty = max(0, pos_qty - qty)
                        # Emit a point when we have a timestamp
                        if ts_iso:
                            realized_pairs.append((ts_iso, float(realized_cum)))
                # Use the derived series if we produced any points
                if realized_pairs:
                    realized = realized_pairs
            except Exception:
                pass

        # Derive bar interval (minutes). Prefer runner result → params → default 1m.
        try:
            bar_interval_minutes = int(result.get("bar_interval_minutes") or params.get("bar_interval_minutes") or 1)
        except Exception:
            bar_interval_minutes = 1

        metrics_series = compute_cumulative_metrics(
            result.get("equity", []) or [],
            realized,
            bar_minutes=bar_interval_minutes,
        )

        # Annualization factor (P) disclosure for transparency
        try:
            minutes_per_session = 390
            sessions_per_year = 252
            periods_per_session = max(1, int(minutes_per_session / max(1, int(bar_interval_minutes))))
            annualization_P = float(periods_per_session * sessions_per_year)
        except Exception:
            annualization_P = float(252 * 390)

        metrics_artifact = {
            "stats": {"raw": nautilus.get("stats", {})},
            "series": metrics_series,
            "bar_interval_minutes": bar_interval_minutes,
            "annualization_P": annualization_P,
        }
        ensure_dir(out_dir)
        metrics_path.write_text(json.dumps(metrics_artifact, indent=2))
        logger.info(f"Artifacts written to {out_dir}")

        # Write manifest
        manifest = {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "strategy_id": strategy_id,
            "params": params,
            "seed": seed,
            "slippage_fees": slippage_fees,
            "speed": speed,
            "run_from": from_date,
            "run_to": to_date,
            "code_hash": code_hash,
            "env_lock": None,
            "calendar_version": "NAZDAQ-v1",
            "tz": "America/New_York",
            "bar_interval_minutes": bar_interval_minutes,
            "created_at": created_at_iso,
            "status": "DONE",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # Finalize DB row to DONE + metrics table
        cat.set_backtest_status(
            run_id,
            status="DONE",
            duration_ms=duration_ms,
            metrics_path=str(metrics_path),
            equity_path=str(equity_path),
            orders_path=str(orders_path),
            fills_path=str(fills_path),
        )
        # NOTE: DB metrics upsert deprecated for this epic; metrics are served via metrics_path artifact.

        return {
            "run_id": run_id,
            "status": "DONE",
            "duration_ms": duration_ms,
            "paths": {
                "metrics": str(metrics_path),
                "equity": str(equity_path),
                "orders": str(orders_path),
                "fills": str(fills_path),
                "manifest": str(manifest_path),
            },
        }
    except BaseException as e:
        # Fail hard: mark as ERROR, write manifest with error, do not write artifacts
        duration_ms = int((time.perf_counter() - t0) * 1000)
        ensure_dir(out_dir)
        error_payload = {
            "error_type": type(e).__name__,
            "error_message": str(e),
        }
        manifest = {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "strategy_id": strategy_id,
            "params": params,
            "seed": seed,
            "slippage_fees": slippage_fees,
            "speed": speed,
            "run_from": from_date,
            "run_to": to_date,
            "code_hash": code_hash,
            "env_lock": None,
            "calendar_version": "NAZDAQ-v1",
            "tz": "America/New_York",
            "created_at": created_at_iso,
            "status": "ERROR",
            "error": error_payload,
        }
        try:
            manifest_path.write_text(json.dumps(manifest, indent=2))
        except Exception:
            pass

        # Update DB row to ERROR; do not set artifact paths
        cat.set_backtest_status(
            run_id,
            status="ERROR",
            duration_ms=duration_ms,
        )

        return {
            "run_id": run_id,
            "status": "ERROR",
            "duration_ms": duration_ms,
            "error": error_payload,
            "paths": {
                "manifest": str(manifest_path),
            },
        }

