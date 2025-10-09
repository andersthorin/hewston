from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

import polars as pl

from backend.adapters.nautilus import NautilusBacktestRunner
from backend.services.backtests import get_catalog
from backend.utils.datetime import utc_now
from backend.utils.git import get_git_commit_hash
from backend.utils.metrics import compute_cumulative_metrics
from backend.utils.paths import ensure_dir, get_backtests_dir

# Configure logging for backtest execution
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _write_parquet(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(records)
    df.write_parquet(path)




def _execute_and_persist_backtest(
    *,
    dataset_id: str | None,
    strategy_id: str,
    params: dict[str, Any],
    seed: int,
    from_date: str | None,
    to_date: str | None,
    speed: int,
    slippage_fees: dict[str, Any],
    cat,
    out_dir: Path,
    out_dir_abs: Path,
    equity_path: Path,
    orders_path: Path,
    fills_path: Path,
    metrics_path: Path,
    manifest_path: Path,
    run_id: str,
    code_hash: str,
    created_at_iso: str,
    logger: logging.Logger,
) -> dict:
    t0 = time.perf_counter()

    logger.info("Initializing Nautilus backtest runner...")
    runner = NautilusBacktestRunner()

    logger.info("Running backtest...")
    result = runner.run(
        dataset_id=dataset_id,
        strategy_id=strategy_id,
        params=params,
        seed=seed,
        from_date=from_date,
        to_date=to_date,
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

    # Canonical equity captured directly from strategy
    equity_records = list(result.get("equity") or [])
    if not equity_records:
        raise RuntimeError(
            "Canonical equity series missing from strategy; cannot persist equity (fail-fast)"
        )

    # Validate equity against Nautilus total_return
    _validate_equity_against_total_return(
        equity_records,
        result.get("metrics") or {},
        start_balance=10000.0,
    )

    _write_parquet(equity_records, equity_path)
    _write_parquet(result.get("orders", []), orders_path)
    _write_parquet(result.get("fills", []), fills_path)

    # Build metrics artifact inputs
    realized = _derive_realized_series_from_result(result)

    # Derive bar interval (minutes)
    try:
        bar_interval_minutes = int(
            result.get("bar_interval_minutes") or params.get("bar_interval_minutes") or 1
        )
    except Exception:
        bar_interval_minutes = 1

    metrics_series = compute_cumulative_metrics(
        equity_records,
        realized,
        bar_minutes=bar_interval_minutes,
    )

    compact_series = _compact_metrics_series(metrics_series)

    end_pos_qty_fills = _compute_end_pos_qty_fills(result.get("fills", []) or [])

    # Annualization factor (P)
    try:
        minutes_per_session = 390
        sessions_per_year = 252
        periods_per_session = max(1, int(minutes_per_session / max(1, int(bar_interval_minutes))))
        annualization_P = float(periods_per_session * sessions_per_year)
    except Exception:
        annualization_P = float(252 * 390)

    nautilus_stats, sr_val = _extract_nautilus_stats_and_sharpe(result)

    metrics_artifact = {
        "stats": {"raw": nautilus_stats},
        "series": compact_series,
        "bar_interval_minutes": bar_interval_minutes,
        "annualization_P": annualization_P,
        "end_pos_qty_fills": float(end_pos_qty_fills),
    }
    if sr_val is not None:
        metrics_artifact["sharpe_ratio"] = sr_val

    # Surface a few canonical Nautilus metrics to top-level if present
    try:
        res_metrics = result.get("metrics") or {}
        for k in ("total_return", "max_drawdown", "win_rate"):
            if res_metrics.get(k) is not None:
                metrics_artifact[k] = float(res_metrics.get(k))
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

    # Finalize DB row
    cat.set_backtest_status(
        run_id,
        status="DONE",
        duration_ms=duration_ms,
        metrics_path=str(metrics_path),
        equity_path=str(equity_path),
        orders_path=str(orders_path),
        fills_path=str(fills_path),
    )

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



def _compact_metrics_series(metrics_series: list[tuple[str, dict]]) -> list:
    """Store only points where realized_pnl or win_rate changes, plus final point."""
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
    if metrics_series:
        last_ts = metrics_series[-1][0]
        if not compact_series or compact_series[-1][0] != last_ts:
            last_m = metrics_series[-1][1]
            compact_series.append(
                [last_ts, {"realized_pnl": last_m.get("realized_pnl"), "win_rate": last_m.get("win_rate")}]
            )
    return compact_series


def _compute_end_pos_qty_fills(fills: list[dict]) -> float:
    end_pos_qty = 0.0
    try:
        for f in fills or []:
            side = (f.get("side") or "").upper()
            qty = float(f.get("qty") or 0.0)
            if side == "BUY":
                end_pos_qty += qty
            elif side == "SELL":
                end_pos_qty -= qty
    except Exception:
        end_pos_qty = 0.0
    return float(end_pos_qty)


def _extract_nautilus_stats_and_sharpe(result: dict[str, Any]) -> tuple[dict, float | None]:
    try:
        nautilus_stats = (result.get("nautilus", {}) or {}).get("stats", {}) or {}
        sr_val = None
        try:
            sr_val = (nautilus_stats.get("returns") or {}).get("Sharpe Ratio (252 days)")
            if sr_val is not None:
                sr_val = float(sr_val)
        except Exception:
            sr_val = None
        return nautilus_stats, sr_val
    except Exception:
        return {}, None



def _validate_equity_against_total_return(
    equity_records: list[dict],
    result_metrics: dict[str, Any] | None,
    *,
    start_balance: float = 10000.0,
) -> None:
    backend_total_return = None
    try:
        backend_total_return = float((result_metrics or {}).get("total_return"))
    except Exception:
        backend_total_return = None
    if backend_total_return is None:
        raise RuntimeError("Nautilus total_return missing; cannot validate equity (fail-fast)")

    expected_final = start_balance * (1.0 + backend_total_return)
    try:
        last_val = float(equity_records[-1]["value"])  # type: ignore[index]
    except Exception:
        last_val = None
    if last_val is None:
        raise RuntimeError("Canonical equity series has invalid last value")

    tol = max(1e-6, 0.001 * abs(expected_final))  # 0.1% relative tolerance
    if abs(last_val - expected_final) > tol:
        raise RuntimeError(
            f"Canonical equity failed validation: expected_final={expected_final:.6f}, last={last_val}"
        )


def _derive_realized_series_from_result(result: dict[str, Any]) -> list[tuple[str, float]]:
    """Return cumulative realized PnL series as [(iso, value), ...].

    Prefer Nautilus analyzer series; if absent, derive from fills conservatively.
    """
    realized: list[tuple[str, float]] = []
    # Prefer Nautilus analyzer series
    try:
        rp = ((result.get("nautilus") or {}).get("series") or {}).get("realized_pnl") or []
        realized = [
            (str(a[0]), float(a[1]))
            for a in rp
            if isinstance(a, (list, tuple)) and len(a) >= 2
        ]
    except Exception:
        realized = []

    if realized:
        return realized

    # Fallback: derive from fills (BUY/SELL pairs), preserving fees
    try:
        from backend.utils.datetime import normalize_timestamp  # local import for isolation

        fills_rows = list(result.get("fills") or [])

        def _key_ts(f: dict) -> tuple[int, str]:
            try:
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
            try:
                _, iso = normalize_timestamp(f.get("ts_utc"))
            except Exception:
                iso = str(f.get("ts_utc") or "")

            if side == "BUY" and qty > 0:
                # Update weighted average entry price
                new_qty = pos_qty + qty
                if new_qty > 0:
                    avg_entry = (
                        (avg_entry * pos_qty + px * qty) / new_qty if pos_qty > 0 else px
                    )
                pos_qty = new_qty
                cum -= fee
            elif side == "SELL" and qty > 0:
                # Realize PnL on sold quantity against average entry
                realized_qty = min(qty, pos_qty) if pos_qty > 0 else 0.0
                pnl = (px - avg_entry) * realized_qty
                cum += pnl
                cum -= fee
                pos_qty = max(0.0, pos_qty - realized_qty)
                if pos_qty == 0.0:
                    avg_entry = 0.0
                realized.append((iso, float(cum)))
        return realized
    except Exception:
        return []

def run_backtest_and_persist(
    *,
    dataset_id: str | None = None,  # Optional - not needed for warehouse-based backtests
    strategy_id: str = "sma_crossover",
    params: dict[str, Any] | None = None,
    seed: int = 42,
    speed: int = 60,
    slippage_fees: dict[str, Any] | None = None,
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
    equity_path = out_dir_abs / "equity.parquet"
    orders_path = out_dir_abs / "orders.parquet"
    fills_path = out_dir_abs / "fills.parquet"
    metrics_path = out_dir_abs / "metrics.json"
    manifest_path = out_dir_abs / "run-manifest.json"

    # Move to RUNNING
    cat.set_backtest_status(run_id, status="RUNNING")

    # Do NOT prepare or derive datasets here; admin-only via CLI/APIs.
    # If dataset is missing/not-ready, the runner will raise and we record ERROR.

    t0 = time.perf_counter()
    try:
        return _execute_and_persist_backtest(
            dataset_id=dataset_id,
            strategy_id=strategy_id,
            params=params,
            seed=seed,
            from_date=from_date,
            to_date=to_date,
            speed=speed,
            slippage_fees=slippage_fees,
            cat=cat,
            out_dir=out_dir,
            out_dir_abs=out_dir_abs,
            equity_path=equity_path,
            orders_path=orders_path,
            fills_path=fills_path,
            metrics_path=metrics_path,
            manifest_path=manifest_path,
            run_id=run_id,
            code_hash=code_hash,
            created_at_iso=created_at_iso,
            logger=logger,
        )
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
