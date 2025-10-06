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

        # Use canonical equity captured directly from Nautilus account.equity_total via strategy (no reconstruction)
        equity_records = list(result.get("equity") or [])
        if not equity_records:
            raise RuntimeError("Canonical equity series missing from strategy; cannot persist equity (fail-fast)")

        # Validate final value against Nautilus total_return
        start_balance = 10000.0
        backend_total_return = None
        try:
            backend_total_return = float((result.get("metrics") or {}).get("total_return"))
        except Exception:
            backend_total_return = None
        if backend_total_return is None:
            raise RuntimeError("Nautilus total_return missing; cannot validate equity (fail-fast)")
        expected_final = start_balance * (1.0 + backend_total_return)
        try:
            last_val = float(equity_records[-1]["value"])  # type: ignore
        except Exception:
            last_val = None
        if last_val is None:
            raise RuntimeError("Canonical equity series has invalid last value")
        tol = max(1e-6, 0.001 * abs(expected_final))  # 0.1% relative tolerance
        if abs(last_val - expected_final) > tol:
            raise RuntimeError(
                f"Canonical equity failed validation: expected_final={expected_final:.6f}, last={last_val}"
            )

        _write_parquet(equity_records, equity_path)
        _write_parquet(result.get("orders", []), orders_path)
        _write_parquet(result.get("fills", []), fills_path)

        # Build metrics artifact: precompute cumulative series aligned to equity timestamps
        realized: list[tuple[str, float]] = []
        try:
            rp = (nautilus.get("series") or {}).get("realized_pnl") or []
            # Expect [[iso,value], ...]
            realized = [(str(a[0]), float(a[1])) for a in rp if isinstance(a, (list, tuple)) and len(a) >= 2]
        except Exception:
            realized = []

        # If Nautilus analyzer did not provide a realized PnL series, derive a cumulative
        # realized PnL series from canonical fills (BUY/SELL pairs). This uses only Nautilus
        # fills data and keeps commissions/slippage if present in fills.
        if not realized:
            try:
                fills_rows = list(result.get("fills") or [])
                # Sort fills by timestamp
                def _key_ts(f):
                    try:
                        from backend.utils.datetime import normalize_timestamp
                        ep, iso = normalize_timestamp(f.get("ts_utc"))
                        return int(ep), iso
                    except Exception:
                        return (0, str(f.get("ts_utc") or ""))
                fills_rows.sort(key=lambda f: _key_ts(f)[0])

                cum = 0.0
                pos_qty = 0.0
                avg_entry = 0.0
                realized = []
                for f in fills_rows:
                    side = (f.get("side") or "").upper()
                    qty = float(f.get("qty") or 0.0)
                    px = float(f.get("price") or 0.0)
                    fee = float(f.get("fee") or 0.0)
                    # timestamp iso
                    try:
                        from backend.utils.datetime import normalize_timestamp
                        _, iso = normalize_timestamp(f.get("ts_utc"))
                    except Exception:
                        iso = str(f.get("ts_utc") or "")

                    if side == "BUY" and qty > 0:
                        # Update weighted average entry price
                        new_qty = pos_qty + qty
                        if new_qty > 0:
                            avg_entry = (avg_entry * pos_qty + px * qty) / new_qty if pos_qty > 0 else px
                        pos_qty = new_qty
                        cum -= fee
                    elif side == "SELL" and qty > 0:
                        # Realize PnL on sold quantity against average entry
                        realized_qty = min(qty, pos_qty) if pos_qty > 0 else 0.0
                        pnl = (px - avg_entry) * realized_qty
                        cum += pnl
                        cum -= fee
                        pos_qty = max(0.0, pos_qty - realized_qty)
                        # If flat, reset avg_entry
                        if pos_qty == 0.0:
                            avg_entry = 0.0
                        realized.append((iso, float(cum)))
                # If we produced no points, leave realized empty
            except Exception:
                realized = []

        # Derive bar interval (minutes). Prefer runner result → params → default 1m.
        try:
            bar_interval_minutes = int(result.get("bar_interval_minutes") or params.get("bar_interval_minutes") or 1)
        except Exception:
            bar_interval_minutes = 1

        metrics_series = compute_cumulative_metrics(
            equity_records,
            realized,
            bar_minutes=bar_interval_minutes,
        )

        # Compact metrics series drastically: store only when realized_pnl or win_rate changes.
        # Also store only those keys; fill others at stream time from equity (cheap) to keep artifact small.
        compact_series: list = []
        prev_rp = object()
        prev_wr = object()
        for ts_iso, m in metrics_series:
            rp = m.get("realized_pnl")
            wr = m.get("win_rate")
            changed = (rp != prev_rp) or (wr != prev_wr)
            if not compact_series or changed:
                compact_series.append([ts_iso, {"realized_pnl": rp, "win_rate": wr}])
                prev_rp, prev_wr = rp, wr
        # Ensure the last timestamp is present (idempotent if unchanged)
        if metrics_series:
            last_ts = metrics_series[-1][0]
            if not compact_series or compact_series[-1][0] != last_ts:
                last_m = metrics_series[-1][1]
                compact_series.append([last_ts, {"realized_pnl": last_m.get("realized_pnl"), "win_rate": last_m.get("win_rate")}])

        # Compute end position qty from fills (diagnostic; net long only for our SMA strategy)
        end_pos_qty_fills = 0.0
        try:
            end_pos_qty_fills = 0.0
            for f in (result.get("fills", []) or []):
                side = (f.get("side") or "").upper()
                qty = float(f.get("qty") or 0.0)
                if side == "BUY":
                    end_pos_qty_fills += qty
                elif side == "SELL":
                    end_pos_qty_fills -= qty
        except Exception:
            end_pos_qty_fills = 0.0

        # Annualization factor (P) disclosure for transparency
        try:
            minutes_per_session = 390
            sessions_per_year = 252
            periods_per_session = max(1, int(minutes_per_session / max(1, int(bar_interval_minutes))))
            annualization_P = float(periods_per_session * sessions_per_year)
        except Exception:
            annualization_P = float(252 * 390)

        # Extract canonical Sharpe from Nautilus raw stats (if available)
        try:
            nautilus_stats = (result.get("nautilus", {}) or {}).get("stats", {}) or {}
            sr_val = None
            try:
                sr_val = (nautilus_stats.get("returns") or {}).get("Sharpe Ratio (252 days)")
                if sr_val is not None:
                    sr_val = float(sr_val)
            except Exception:
                sr_val = None
        except Exception:
            nautilus_stats = {}
            sr_val = None

        metrics_artifact = {
            "stats": {"raw": nautilus_stats},
            "series": compact_series,
            "bar_interval_minutes": bar_interval_minutes,
            "annualization_P": annualization_P,
            "end_pos_qty_fills": float(end_pos_qty_fills),
        }
        if sr_val is not None:
            metrics_artifact["sharpe_ratio"] = sr_val
        # If we have a realized series, expose its last point for summary display
        try:
            if compact_series:
                last_ts = compact_series[-1][0]
                # find last realized pnl in metrics_series by timestamp match
                try:
                    last_m = next((m for ts_iso, m in metrics_series[::-1] if ts_iso == last_ts), None)
                except Exception:
                    last_m = metrics_series[-1][1] if metrics_series else None
                if last_m and last_m.get("realized_pnl") is not None:
                    metrics_artifact["realized_pnl"] = float(last_m.get("realized_pnl"))
        except Exception:
            pass
        try:
            res_metrics = (result.get("metrics") or {})
            # Promote canonical Nautilus metrics to top-level for final UI override
            for k in ("total_return", "max_drawdown", "win_rate"):
                if res_metrics.get(k) is not None:
                    metrics_artifact[k] = float(res_metrics.get(k))
            # Also surface ending balance, unrealized PnL, and ending equity if present
            if res_metrics.get("ending_balance") is not None:
                metrics_artifact["ending_balance"] = float(res_metrics.get("ending_balance"))
            if res_metrics.get("unrealized_pnl") is not None:
                metrics_artifact["unrealized_pnl"] = float(res_metrics.get("unrealized_pnl"))
            if res_metrics.get("ending_equity") is not None:
                metrics_artifact["ending_equity"] = float(res_metrics.get("ending_equity"))
            if res_metrics.get("end_position_qty") is not None:
                metrics_artifact["end_pos_qty_nautilus"] = float(res_metrics.get("end_position_qty"))
        except Exception:
            pass

        ensure_dir(out_dir)
        # Write minified JSON to reduce file size further
        metrics_path.write_text(json.dumps(metrics_artifact, separators=(",", ":")))
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

