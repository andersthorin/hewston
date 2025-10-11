"""Backtest execution job: runs Nautilus and persists canonical artifacts."""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import suppress
from pathlib import Path
from typing import Any

import polars as pl

from backend.adapters.nautilus import NautilusBacktestRunner, RunSpec
from backend.services.backtests import get_catalog
from backend.utils.datetime import utc_now
from backend.utils.git import get_git_commit_hash
from backend.utils.metrics import compute_cumulative_metrics
from backend.utils.paths import ensure_dir, get_backtests_dir

# Configure logging for backtest execution
# Minimum items required in a series entry like [ts, value]
MIN_SERIES_LEN = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _write_parquet(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(records)
    df.write_parquet(path)


def _execute_and_persist_backtest(*, args: dict[str, Any]) -> dict:
    """Execute Nautilus, write artifacts, and return a summary.

    Args holds all required fields (dataset/strategy/spec, paths, ids, etc.).
    """
    # Unpack frequently used fields locally for readability
    dataset_id = args.get("dataset_id")
    strategy_id = args["strategy_id"]
    params = args["params"]
    seed = args["seed"]
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    equity_path = args["equity_path"]
    orders_path = args["orders_path"]
    fills_path = args["fills_path"]
    logger: logging.Logger = args["logger"]

    t0 = time.perf_counter()

    logger.info("Initializing Nautilus backtest runner...")
    runner = NautilusBacktestRunner()

    logger.info("Running backtest...")
    result = runner.run(
        spec=RunSpec(
            dataset_id=dataset_id,
            strategy_id=strategy_id,
            params=params,
            seed=seed,
            from_date=from_date,
            to_date=to_date,
        )
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
    annualization_p = _compute_annualization_p(bar_interval_minutes)

    nautilus_stats, sr_val = _extract_nautilus_stats_and_sharpe(result)

    metrics_artifact = {
        "stats": {"raw": nautilus_stats},
        "series": compact_series,
        "bar_interval_minutes": bar_interval_minutes,
        "annualization_P": annualization_p,
        "end_pos_qty_fills": float(end_pos_qty_fills),
    }
    if sr_val is not None:
        metrics_artifact["sharpe_ratio"] = sr_val

    # Surface a few canonical Nautilus metrics to top-level if present
    res_metrics = result.get("metrics") or {}
    _surface_nautilus_metrics(metrics_artifact, res_metrics)

    return _persist_artifacts_and_finalize(
        args=args,
        metrics_artifact=metrics_artifact,
        bar_interval_minutes=bar_interval_minutes,
        duration_ms=duration_ms,
    )


# --- Multi-strategy helpers (Epic 20) ---

def _run_single_strategy_to_paths(*, args: dict[str, Any]) -> dict:
    """Run a single strategy and write artifacts to provided paths, returning metrics_artifact.
    Expects same args keys as _execute_and_persist_backtest but does NOT finalize DB status.
    """
    dataset_id = args.get("dataset_id")
    strategy_id = args["strategy_id"]
    params = args["params"]
    seed = args["seed"]
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    equity_path = args["equity_path"]
    orders_path = args["orders_path"]
    fills_path = args["fills_path"]
    logger: logging.Logger = args["logger"]

    t0 = time.perf_counter()
    runner = NautilusBacktestRunner()
    result = runner.run(
        spec=RunSpec(
            dataset_id=dataset_id,
            strategy_id=strategy_id,
            params=params,
            seed=seed,
            from_date=from_date,
            to_date=to_date,
        )
    )
    duration_ms = int((time.perf_counter() - t0) * 1000)

    equity_records = list(result.get("equity") or [])
    if not equity_records:
        raise RuntimeError("Canonical equity series missing from strategy; cannot persist equity (fail-fast)")

    _validate_equity_against_total_return(
        equity_records,
        result.get("metrics") or {},
        start_balance=10000.0,
    )

    _write_parquet(equity_records, equity_path)
    _write_parquet(result.get("orders", []), orders_path)
    _write_parquet(result.get("fills", []), fills_path)

    try:
        bar_interval_minutes = int(result.get("bar_interval_minutes") or params.get("bar_interval_minutes") or 1)
    except Exception:
        bar_interval_minutes = 1

    realized = _derive_realized_series_from_result(result)
    metrics_series = compute_cumulative_metrics(equity_records, realized, bar_minutes=bar_interval_minutes)
    compact_series = _compact_metrics_series(metrics_series)
    end_pos_qty_fills = _compute_end_pos_qty_fills(result.get("fills", []) or [])
    annualization_p = _compute_annualization_p(bar_interval_minutes)
    nautilus_stats, sr_val = _extract_nautilus_stats_and_sharpe(result)

    metrics_artifact = {
        "stats": {"raw": nautilus_stats},
        "series": compact_series,
        "bar_interval_minutes": bar_interval_minutes,
        "annualization_P": annualization_p,
        "end_pos_qty_fills": float(end_pos_qty_fills),
    }
    if sr_val is not None:
        metrics_artifact["sharpe_ratio"] = sr_val
    _surface_nautilus_metrics(metrics_artifact, result.get("metrics") or {})
    return {"metrics": metrics_artifact, "duration_ms": duration_ms}


def _finalize_multi_run(*, args: dict[str, Any], per_strategy: dict[str, dict]) -> dict:
    """Finalize a multi-strategy run: write combined metrics and manifest, update DB once."""
    out_dir: Path = args["out_dir"]
    metrics_path: Path = args["metrics_path"]  # will write combined here
    logger: logging.Logger = args["logger"]
    run_id: str = args["run_id"]
    dataset_id = args.get("dataset_id")
    seed: int = args["seed"]
    slippage_fees: dict[str, Any] = args["slippage_fees"]
    speed: int = args["speed"]
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    code_hash: str = args["code_hash"]
    created_at_iso: str = args["created_at_iso"]
    cat = args["cat"]
    manifest_path: Path = args["manifest_path"]

    ensure_dir(out_dir)

    # Build combined metrics summary (simple aggregation)
    summary = {}
    try:
        # pick best by total_return if available
        best = None
        for sid, arts in per_strategy.items():
            m = (arts.get("metrics") or {})
            tr = m.get("total_return")
            if tr is not None:
                if best is None or float(tr) > float(best[1]):
                    best = (sid, float(tr))
        if best:
            summary["best_total_return_strategy"] = best[0]
            summary["best_total_return"] = best[1]
    except Exception:
        pass

    combined = {"per_strategy": {k: {"metrics": v.get("metrics")} for k, v in per_strategy.items()}, "summary": summary}
    metrics_path.write_text(json.dumps(combined, separators=(",", ":")))
    logger.info(f"Wrote combined metrics for multi-strategy run: {metrics_path}")

    # Merge with minimal manifest and include strategies list if present in args
    base = {}
    try:
        if manifest_path.is_file():
            base = json.loads(manifest_path.read_text() or "{}")
    except Exception:
        base = {}

    # Persist per-strategy artifact paths in manifest to aid API lookups
    per_strategy_artifacts = {
        sid: {
            "equity_path": str((out_dir / f"strategy={sid}" / "equity.parquet").resolve()),
            "orders_path": str((out_dir / f"strategy={sid}" / "orders.parquet").resolve()),
            "fills_path": str((out_dir / f"strategy={sid}" / "fills.parquet").resolve()),
            "metrics_path": str((out_dir / f"strategy={sid}" / "metrics.json").resolve()),
        }
        for sid in per_strategy.keys()
    }

    manifest = {
        **(base or {}),
        "run_id": run_id,
        "dataset_id": dataset_id,
        # Keep compatibility fields if base has them; do not overwrite strategy_id/params for multi
        "seed": seed,
        "slippage_fees": slippage_fees,
        "speed": speed,
        "run_from": from_date,
        "run_to": to_date,
        "code_hash": code_hash,
        "env_lock": base.get("env_lock") if isinstance(base, dict) else None,
        "calendar_version": base.get("calendar_version") if isinstance(base, dict) else "NAZDAQ-v1",
        "tz": base.get("tz") if isinstance(base, dict) else "America/New_York",
        "created_at": base.get("created_at") or created_at_iso,
        "status": "DONE",
        "per_strategy_artifacts": per_strategy_artifacts,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Set DB status and store combined metrics path under metrics_path for compatibility
    cat.set_backtest_status(
        run_id,
        status="DONE",
        duration_ms=sum((v.get("duration_ms") or 0) for v in per_strategy.values()),
        artifacts={
            "metrics_path": str(metrics_path),
            "run_manifest_path": str(manifest_path),
        },
    )

    return {
        "run_id": run_id,
        "status": "DONE",
        "paths": {
            "combined_metrics": str(metrics_path),
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
                [
                    last_ts,
                    {
                        "realized_pnl": last_m.get("realized_pnl"),
                        "win_rate": last_m.get("win_rate"),
                    },
                ]
            )
    return compact_series


def _compute_annualization_p(bar_interval_minutes: int) -> float:
    try:
        minutes_per_session = 390
        sessions_per_year = 252
        periods_per_session = max(1, int(minutes_per_session / max(1, int(bar_interval_minutes))))
        return float(periods_per_session * sessions_per_year)
    except Exception:
        return float(252 * 390)


def _surface_nautilus_metrics(metrics_artifact: dict, res_metrics: dict) -> None:
    try:
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


def _persist_artifacts_and_finalize(
    *,
    args: dict[str, Any],
    metrics_artifact: dict,
    bar_interval_minutes: int,
    duration_ms: int,
) -> dict:
    out_dir: Path = args["out_dir"]
    metrics_path: Path = args["metrics_path"]
    logger: logging.Logger = args["logger"]
    run_id: str = args["run_id"]
    dataset_id = args.get("dataset_id")
    strategy_id: str = args["strategy_id"]
    params: dict[str, Any] = args["params"]
    seed: int = args["seed"]
    slippage_fees: dict[str, Any] = args["slippage_fees"]
    speed: int = args["speed"]
    from_date = args.get("from_date")
    to_date = args.get("to_date")
    code_hash: str = args["code_hash"]
    created_at_iso: str = args["created_at_iso"]
    cat = args["cat"]
    equity_path: Path = args["equity_path"]
    orders_path: Path = args["orders_path"]
    fills_path: Path = args["fills_path"]
    manifest_path: Path = args["manifest_path"]

    ensure_dir(out_dir)
    metrics_path.write_text(json.dumps(metrics_artifact, separators=(",", ":")))
    logger.info(f"Artifacts written to {out_dir}")

    # Merge with any existing minimal manifest (to preserve agentic_plan, etc.)
    base = {}
    try:
        if manifest_path.is_file():
            base = json.loads(manifest_path.read_text() or "{}")
    except Exception:
        base = {}

    manifest = {
        **(base or {}),
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
        "env_lock": base.get("env_lock") if isinstance(base, dict) else None,
        "calendar_version": base.get("calendar_version") if isinstance(base, dict) else "NAZDAQ-v1",
        "tz": base.get("tz") if isinstance(base, dict) else "America/New_York",
        "bar_interval_minutes": bar_interval_minutes,
        "created_at": base.get("created_at") or created_at_iso,
        "status": "DONE",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    cat.set_backtest_status(
        run_id,
        status="DONE",
        duration_ms=duration_ms,
        artifacts={
            "metrics_path": str(metrics_path),
            "equity_path": str(equity_path),
            "orders_path": str(orders_path),
            "fills_path": str(fills_path),
        },
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


def _read_nautilus_realized_series(result: dict[str, Any]) -> list[tuple[str, float]]:
    try:
        rp = ((result.get("nautilus") or {}).get("series") or {}).get("realized_pnl") or []
        return [
            (str(a[0]), float(a[1]))
            for a in rp
            if isinstance(a, list | tuple) and len(a) >= MIN_SERIES_LEN
        ]
    except Exception:
        return []


def _derive_realized_from_fills(result: dict[str, Any]) -> list[tuple[str, float]]:
    try:
        from backend.utils.datetime import normalize_timestamp

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
        realized: list[tuple[str, float]] = []
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
                new_qty = pos_qty + qty
                if new_qty > 0:
                    avg_entry = (avg_entry * pos_qty + px * qty) / new_qty if pos_qty > 0 else px
                pos_qty = new_qty
                cum -= fee
            elif side == "SELL" and qty > 0:
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
            "Canonical equity failed validation: "
            f"expected_final={expected_final:.6f}, last={last_val}"
        )


def _derive_realized_series_from_result(result: dict[str, Any]) -> list[tuple[str, float]]:
    """Return cumulative realized PnL series as [(iso, value), ...].

    Prefer Nautilus analyzer series; if absent, derive from fills conservatively.
    """
    realized = _read_nautilus_realized_series(result)
    if realized:
        return realized
    return _derive_realized_from_fills(result)


def run_backtest_and_persist(*, req: dict[str, Any]) -> dict:
    """Run a Nautilus backtest and persist artifacts under backtests/<run_id>.

    Returns the final manifest dict.
    """
    logger = logging.getLogger("backtest.job")
    dataset_id = req.get("dataset_id")
    strategy_id = req.get("strategy_id", "sma_crossover")
    params = req.get("params") or {}
    seed = int(req.get("seed", 42))
    speed = int(req.get("speed", 60))
    slippage_fees = req.get("slippage_fees") or {}
    run_id = req.get("run_id")
    from_date = req.get("from_date")
    to_date = req.get("to_date")
    cat = get_catalog()

    """Run a Nautilus backtest and persist artifacts under backtests/<run_id>.

    Returns the final manifest dict.
    """

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
            row={
                "run_id": run_id,
                "dataset_id": dataset_id,
                "strategy_id": strategy_id,
                "params_json": json.dumps(params, sort_keys=True),
                "seed": seed,
                "slippage_fees_json": json.dumps(slippage_fees, sort_keys=True),
                "speed": speed,
                "code_hash": code_hash,
                "created_at": created_at_iso,
                "status": "QUEUED",
                "run_manifest_path": str(manifest_path_tmp),
                "input_hash": None,
                "idempotency_key": None,
            }
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
        strategies = req.get("strategies") or []
        if isinstance(strategies, list) and strategies:
            # Multi-strategy: run all strategies in a single engine/portfolio (Option A)
            runner = NautilusBacktestRunner()
            specs = [
                RunSpec(
                    dataset_id=dataset_id,
                    strategy_id=(s or {}).get("strategy_id"),
                    params=(s or {}).get("params") or {},
                    seed=seed,
                    from_date=from_date,
                    to_date=to_date,
                )
                for s in strategies
                if (s or {}).get("strategy_id")
            ]
            result_multi = runner.run_multi(specs=specs)

            # Write portfolio-level artifacts at run root
            _write_parquet(list(result_multi.get("equity") or []), equity_path)
            _write_parquet(list(result_multi.get("orders") or []), orders_path)
            _write_parquet(list(result_multi.get("fills") or []), fills_path)

            # Also write per-strategy diagnostics into subdirectories
            per_map = result_multi.get("per_strategy") or {}
            for sid, diag in per_map.items():
                subdir = out_dir_abs / f"strategy={sid}"
                ensure_dir(subdir)
                _write_parquet(list(diag.get("equity") or []), subdir / "equity.parquet")
                _write_parquet(list(diag.get("orders") or []), subdir / "orders.parquet")
                _write_parquet(list(diag.get("fills") or []), subdir / "fills.parquet")
                # Minimal per-strategy metrics from analyzer returns are not precomputed here
                Path(subdir / "metrics.json").write_text(json.dumps({"note": "diagnostic-only"}))

            # And per-instrument diagnostics when portfolio uses multiple instruments
            per_instr = result_multi.get("per_instrument") or {}
            for iid, diag in per_instr.items():
                subdir = out_dir_abs / f"instrument={iid}"
                ensure_dir(subdir)
                _write_parquet(list(diag.get("equity") or []), subdir / "equity.parquet")
                _write_parquet(list(diag.get("orders") or []), subdir / "orders.parquet")
                _write_parquet(list(diag.get("fills") or []), subdir / "fills.parquet")
                Path(subdir / "metrics.json").write_text(json.dumps({"note": "diagnostic-only"}))

            # Build metrics_artifact using portfolio equity + realized series (from Nautilus analyzer if present)
            try:
                bar_interval_minutes = int(result_multi.get("bar_interval_minutes") or 1)
            except Exception:
                bar_interval_minutes = 1
            equity_records = list(result_multi.get("equity") or [])
            realized_pairs = (((result_multi.get("nautilus") or {}).get("series") or {}).get("realized_pnl") or [])
            realized_series = []
            try:
                for pair in realized_pairs:
                    ts, val = pair[0], float(pair[1])
                    realized_series.append((str(ts), float(val)))
            except Exception:
                realized_series = []

            metrics_series = compute_cumulative_metrics(equity_records, realized_series, bar_minutes=bar_interval_minutes)
            compact_series = _compact_metrics_series(metrics_series)
            end_pos_qty_fills = _compute_end_pos_qty_fills(list(result_multi.get("fills") or []))
            annualization_p = _compute_annualization_p(bar_interval_minutes)
            nautilus_stats = ((result_multi.get("nautilus") or {}).get("stats") or {})
            metrics_artifact = {
                "stats": {"raw": nautilus_stats},
                "series": compact_series,
                "bar_interval_minutes": bar_interval_minutes,
                "annualization_P": annualization_p,
                "end_pos_qty_fills": float(end_pos_qty_fills),
            }
            _surface_nautilus_metrics(metrics_artifact, dict(result_multi.get("metrics") or {}))

            # Persist portfolio artifacts and update DB
            summary = _persist_artifacts_and_finalize(
                args={
                    "dataset_id": dataset_id,
                    "strategy_id": strategy_id,
                    "params": params,
                    "seed": seed,
                    "from_date": from_date,
                    "to_date": to_date,
                    "speed": speed,
                    "slippage_fees": slippage_fees,
                    "cat": cat,
                    "out_dir": out_dir,
                    "out_dir_abs": out_dir_abs,
                    "equity_path": equity_path,
                    "orders_path": orders_path,
                    "fills_path": fills_path,
                    "metrics_path": metrics_path,
                    "manifest_path": manifest_path,
                    "run_id": run_id,
                    "code_hash": code_hash,
                    "created_at_iso": created_at_iso,
                    "logger": logger,
                },
                metrics_artifact=metrics_artifact,
                bar_interval_minutes=bar_interval_minutes,
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )

            # Enrich manifest with per-strategy and per-instrument artifact mappings for diagnostics
            try:
                base = json.loads(manifest_path.read_text() or "{}") if manifest_path.is_file() else {}
                # Per-strategy artifacts
                per_strategy_artifacts = {
                    str(sid): {
                        "equity_path": str((out_dir_abs / f"strategy={sid}" / "equity.parquet").resolve()),
                        "orders_path": str((out_dir_abs / f"strategy={sid}" / "orders.parquet").resolve()),
                        "fills_path": str((out_dir_abs / f"strategy={sid}" / "fills.parquet").resolve()),
                        "metrics_path": str((out_dir_abs / f"strategy={sid}" / "metrics.json").resolve()),
                    }
                    for sid in per_map.keys()
                }
                base["per_strategy_artifacts"] = per_strategy_artifacts

                # Per-instrument artifacts, when present
                per_instr = result_multi.get("per_instrument") or {}
                if per_instr:
                    per_instrument_artifacts = {
                        str(iid): {
                            "equity_path": str((out_dir_abs / f"instrument={iid}" / "equity.parquet").resolve()),
                            "orders_path": str((out_dir_abs / f"instrument={iid}" / "orders.parquet").resolve()),
                            "fills_path": str((out_dir_abs / f"instrument={iid}" / "fills.parquet").resolve()),
                            "metrics_path": str((out_dir_abs / f"instrument={iid}" / "metrics.json").resolve()),
                        }
                        for iid in per_instr.keys()
                    }
                    base["per_instrument_artifacts"] = per_instrument_artifacts
                    instruments = list(result_multi.get("instruments") or [])
                    if instruments:
                        base["instruments"] = instruments

                manifest_path.write_text(json.dumps(base, indent=2))
            except Exception:
                pass

            return summary
        else:
            # Single-strategy path (existing behavior)
            return _execute_and_persist_backtest(
                args={
                    "dataset_id": dataset_id,
                    "strategy_id": strategy_id,
                    "params": params,
                    "seed": seed,
                    "from_date": from_date,
                    "to_date": to_date,
                    "speed": speed,
                    "slippage_fees": slippage_fees,
                    "cat": cat,
                    "out_dir": out_dir,
                    "out_dir_abs": out_dir_abs,
                    "equity_path": equity_path,
                    "orders_path": orders_path,
                    "fills_path": fills_path,
                    "metrics_path": metrics_path,
                    "manifest_path": manifest_path,
                    "run_id": run_id,
                    "code_hash": code_hash,
                    "created_at_iso": created_at_iso,
                    "logger": logger,
                },
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
        with suppress(Exception):
            manifest_path.write_text(json.dumps(manifest, indent=2))

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
