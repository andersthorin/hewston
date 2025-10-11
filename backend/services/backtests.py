"""Service layer for backtests: catalog access and orchestration."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
from datetime import UTC
from typing import Any

from backend.domain.queries import BacktestListQuery
from backend.ports.catalog import CatalogPort


def get_catalog() -> CatalogPort:
    """Resolve catalog location without static dependency on adapters.

    Uses importlib to load SqliteCatalog dynamically to keep services decoupled.
    - If HEWSTON_CATALOG_PATH is set, use that
    - If running under pytest (PYTEST_CURRENT_TEST) without explicit path,
      return a fresh in-memory DB per call
    - Otherwise, use default persistent path.
    """
    import importlib

    path = os.getenv("HEWSTON_CATALOG_PATH")
    module = importlib.import_module("backend.adapters.sqlite_catalog")
    sqlite_catalog_cls = module.SqliteCatalog
    if not path and os.getenv("PYTEST_CURRENT_TEST"):
        return sqlite_catalog_cls(":memory:")  # type: ignore[return-value]
    return sqlite_catalog_cls(path)  # type: ignore[return-value]


def list_backtests_service(q: BacktestListQuery) -> dict[str, Any]:
    """List backtests with optional filters and pagination.

    Args:
      q: Backtest list query parameters.

    Returns:
      dict: {items, total, limit, offset}.
    """
    # Sanitize inputs per story
    limit = max(1, min(int(q.limit), 500))
    offset = max(0, int(q.offset))
    allowed_orders = {"created_at", "-created_at"}
    order = q.order if q.order in allowed_orders else "-created_at"

    from backend.domain.queries import BacktestListQuery

    q_norm = BacktestListQuery(
        symbol=q.symbol,
        strategy_id=q.strategy_id,
        from_date=q.from_date,
        to_date=q.to_date,
        limit=limit,
        offset=offset,
        order=order,
    )

    catalog = get_catalog()
    try:
        items, total = catalog.list_backtests(q_norm)
    except Exception:
        # If catalog not initialized yet, return empty defaults
        return {"items": [], "total": 0, "limit": limit, "offset": offset}
    # Map RunSummary models to dicts for JSON and enrich with run_from/run_to from manifest
    resp_items = []
    import json as _json

    for i in items:
        d = i.model_dump()
        # Remove dataset bounds from response to avoid confusion
        d.pop("from_date", None)
        d.pop("to_date", None)
        # Read run manifest to source authoritative window and portfolio hints
        try:
            run_full = catalog.get_backtest(i.run_id)
            mp = (run_full.get("artifacts") or {}).get("run_manifest_path") if run_full else None
            if mp and os.path.isfile(mp):
                with open(mp) as f:
                    m = _json.load(f)
                rf = m.get("run_from")
                rt = m.get("run_to")
                if rf is not None:
                    d["run_from"] = rf
                if rt is not None:
                    d["run_to"] = rt
                # Portfolio surfacing: instruments/strategies counts and flag
                try:
                    instruments = m.get("instruments") or []
                    per_strategy = (m.get("per_strategy_artifacts") or {})
                    d["instruments_count"] = int(len(instruments)) if instruments else 0
                    d["strategies_count"] = int(len(per_strategy.keys())) if per_strategy else 0
                    d["is_portfolio"] = bool(d.get("instruments_count", 0) and d["instruments_count"] > 1)
                except Exception:
                    pass
        except Exception:
            # Best-effort enrichment; if missing, leave as None
            pass
        resp_items.append(d)
    return {"items": resp_items, "total": total, "limit": limit, "offset": offset}


def get_backtest_service(run_id: str) -> dict | None:
    """Get a single backtest row enriched with run_from/run_to when available.

    Args:
      run_id: Backtest identifier.

    Returns:
      dict | None: The backtest record, or None if not found.
    """
    catalog = get_catalog()
    try:
        run = catalog.get_backtest(run_id)
    except Exception:
        return None
    if not run:
        return None
    # Enrich with run_from/run_to from run-manifest.json when available

    try:
        mp = (run.get("artifacts") or {}).get("run_manifest_path") or (
            run.get("manifest") or {}
        ).get("path")
        if mp:
            import json as _json
            import os

            if os.path.isfile(mp):
                with open(mp) as f:
                    m = _json.load(f)
                rf = m.get("run_from")
                rt = m.get("run_to")
                if rf is not None:
                    run["run_from"] = rf
                if rt is not None:
                    run["run_to"] = rt
    except Exception:
        # Best-effort; ignore enrichment errors
        pass
    return run


# Fallback in-memory idempotency for minimal body (no dataset info)
_IDEMP_CACHE: dict[str, str] = {}


def _parse_iso8601(s: str) -> bool:
    """Accept YYYY-MM-DD or full ISO formats (with Z or offset)."""
    if not isinstance(s, str) or not s:
        return False
    ss = s.replace("Z", "+00:00")
    try:
        from datetime import datetime

        # Accept full ISO or date-only
        datetime.fromisoformat(ss)
        return True
    except Exception:
        return False


def _write_minimal_manifest(*, manifest_path: str, manifest: dict) -> None:
    """Best-effort write of a minimal manifest; safe to fail silently."""
    try:
        from pathlib import Path as _Path

        from backend.utils.paths import ensure_dir as _ensure
        from backend.utils.paths import get_backtests_dir

        _ensure(get_backtests_dir(manifest.get("run_id")))
        _Path(manifest_path).write_text(json.dumps(manifest, indent=2))
    except Exception:
        # Runner will overwrite with full manifest later
        pass


def _enqueue_run_background(*, job_args: dict) -> None:
    """Start background process to run backtest; non-blocking."""
    # Dynamically import job to avoid static dependency on jobs/adapters
    import importlib

    run_job_mod = importlib.import_module("backend.jobs.run_backtest")
    p = multiprocessing.Process(
        target=run_job_mod.run_backtest_and_persist,
        kwargs={"req": job_args},
        daemon=True,
    )
    p.start()


def _validate_strategy_and_dates(
    strategy_id: str | None, run_from: str | None, run_to: str | None, *, strategies: list[dict] | None = None
) -> tuple[dict | None, int | None]:
    # Accept either a single strategy_id or a non-empty strategies list (Epic 20)
    if not strategy_id:
        if not (isinstance(strategies, list) and len(strategies) > 0 and all(isinstance(s, dict) for s in strategies)):
            return {
                "error": {"code": "BAD_REQUEST", "message": "Missing required parameter: strategy_id or strategies[]"}
            }, 400
    if run_from and not _parse_iso8601(run_from):
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "Invalid date format in 'run_from' (expected ISO 8601 YYYY-MM-DD)",
            }
        }, 400
    if run_to and not _parse_iso8601(run_to):
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "Invalid date format in 'run_to' (expected ISO 8601 YYYY-MM-DD)",
            }
        }, 400
    return None, None


def _resolve_dataset_id_and_symbol(
    body: dict,
) -> tuple[str | None, str | None, dict | None, int | None]:
    dataset_id = body.get("dataset_id")
    symbol = body.get("symbol")
    if not dataset_id:
        if not symbol:
            return (
                None,
                None,
                {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Missing required parameter: dataset_id or (symbol + year)",
                    }
                },
                400,
            )
        dataset_id = f"{symbol}-warehouse-1m"
    return dataset_id, symbol, None, None


def _ensure_placeholder_dataset_row(
    catalog, dataset_id: str | None, symbol: str | None, run_from: str | None, run_to: str | None
) -> None:
    if dataset_id and symbol:
        try:
            from datetime import datetime

            catalog.upsert_dataset(
                {
                    "dataset_id": dataset_id,
                    "symbol": symbol,
                    "from_date": run_from,
                    "to_date": run_to,
                    "products": [],
                    "raw_dbn": [],
                    "bars_parquet": [],
                    "bars_manifest_path": None,
                    "generated_at": datetime.now(UTC).isoformat(),
                    "size_bytes": 0,
                    "status": "BUILDING",
                }
            )
        except Exception:
            pass


def _check_idempotency_catalog(
    catalog, input_hash: str, idempotency_key: str | None
) -> dict | None:
    if idempotency_key:
        existing = catalog.find_backtest_by_idempotency_key(idempotency_key)
        if existing:
            return existing
    existing = catalog.find_backtest_by_input_hash(input_hash)
    return existing


def _persist_queued_run_and_manifest(
    catalog,
    *,
    creation: dict,
) -> tuple[str, bool]:
    run_id = creation["run_id"]
    dataset_id = creation["dataset_id"]
    strategy_id = creation["strategy_id"]
    params = creation["params"]
    seed = creation["seed"]
    slippage_fees = creation["slippage_fees"]
    speed = creation["speed"]
    created_at = creation["created_at"]
    manifest_path = creation["manifest_path"]
    input_hash = creation["input_hash"]
    idempotency_key = creation.get("idempotency_key")
    agentic_plan = creation.get("agentic_plan")
    agentic_plan_hash = creation.get("agentic_plan_hash")
    agentic_consent = creation.get("agentic_consent")
    strategies = creation.get("strategies") if isinstance(creation.get("strategies"), list) else None

    # Insert row; if it already exists, treat as EXISTS
    try:
        catalog.create_backtest(
            row={
                "run_id": run_id,
                "dataset_id": dataset_id,
                "strategy_id": strategy_id,
                "params_json": json.dumps(params, sort_keys=True),
                "seed": seed,
                "slippage_fees_json": json.dumps(slippage_fees, sort_keys=True),
                "speed": speed,
                "code_hash": "unknown",
                "created_at": created_at,
                "status": "QUEUED",
                "run_manifest_path": manifest_path,
                "input_hash": input_hash,
                "idempotency_key": idempotency_key,
            }
        )
    except Exception:
        existing = catalog.find_backtest_by_input_hash(creation["input_hash"])  # type: ignore[index]
        if existing:
            return existing["run_id"], True
        raise

    # Best-effort manifest write (must not flip existed=True)
    try:
        minimal_manifest = {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "strategy_id": strategy_id,
            "params": params,
            "seed": seed,
            "slippage_fees": slippage_fees,
            "speed": speed,
            "run_from": None,
            "run_to": None,
            "code_hash": "unknown",
            "created_at": created_at,
            "tz": "America/New_York",
        }
        # Persist multi-strategy set for runner to pick up (compat: keep top-level too)
        if strategies:
            minimal_manifest["strategies"] = [
                {"strategy_id": s.get("strategy_id"), "params": s.get("params") or {}}
                for s in strategies
                if isinstance(s, dict)
            ]
        if agentic_plan is not None:
            minimal_manifest["agentic_plan"] = agentic_plan
            if not agentic_plan_hash:
                try:
                    agentic_plan_hash = _canonical_inputs_hash(agentic_plan)
                except Exception:
                    agentic_plan_hash = None
            if agentic_plan_hash:
                minimal_manifest["agentic_plan_hash"] = agentic_plan_hash
        if agentic_consent is not None:
            minimal_manifest["agentic_consent"] = agentic_consent
        # Persist multi-strategy set for runner to pick up (compat: keep top-level too)
        if strategies:
            try:
                minimal_manifest["strategies"] = [
                    {"strategy_id": s.get("strategy_id"), "params": s.get("params") or {}}
                    for s in strategies
                    if isinstance(s, dict)
                ]
            except Exception:
                pass
        _write_minimal_manifest(manifest_path=manifest_path, manifest=minimal_manifest)
    except Exception:
        pass

    return run_id, False


def _update_idemp_cache(mem_key: str, mem_idemp_key: str | None, run_id: str) -> None:
    _IDEMP_CACHE[mem_key] = run_id
    if mem_idemp_key:
        _IDEMP_CACHE[mem_idemp_key] = run_id


def _canonical_inputs_hash(payload: dict) -> str:
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def create_backtest_service(body: dict, idempotency_key: str | None) -> tuple[dict, int]:
    """Create a backtest row, write a minimal manifest, and enqueue the runner.

    Applies idempotency by header key and canonical input hash.

    Args:
      body: JSON payload from request.
      idempotency_key: Optional idempotency header value.

    Returns:
      tuple[dict, int]: (payload, HTTP status code).
    """
    strategy_id = body.get("strategy_id")
    params = body.get("params", {})
    seed = int(body.get("seed", 42))
    speed = int(body.get("speed", 60))
    slippage_fees = body.get("slippage_fees", {})
    run_from = body.get("run_from")
    run_to = body.get("run_to")

    # Validate required and date fields (single or multi-strategy)
    strategies = body.get("strategies") if isinstance(body.get("strategies"), list) else None
    err, code = _validate_strategy_and_dates(strategy_id, run_from, run_to, strategies=strategies)
    if err:
        return err, code  # type: ignore[return-value]


    # Resolve dataset and symbol with warehouse defaulting
    dataset_id, symbol, derr, dcode = _resolve_dataset_id_and_symbol(body)
    if derr:
        return derr, dcode  # type: ignore[return-value]

    catalog = get_catalog()

    # Ensure placeholder dataset row (best-effort)
    _ensure_placeholder_dataset_row(catalog, dataset_id, symbol, run_from, run_to)

    # Compute deterministic input hash
    inputs_for_hash = {
        "dataset_id": dataset_id,
        "strategy_id": strategy_id,
        "params": params,
        "seed": seed,
        "slippage_fees": slippage_fees,
        "speed": speed,
        "run_from": run_from,
        "run_to": run_to,
    }
    # Include multi-strategy set in canonical hash if provided
    if strategies:
        try:
            inputs_for_hash["strategies"] = [
                {"strategy_id": s.get("strategy_id"), "params": s.get("params") or {}}
                for s in strategies
                if isinstance(s, dict)
            ]
        except Exception:
            pass
    input_hash = _canonical_inputs_hash(inputs_for_hash)

    # Optional: agentic plan passthrough for manifest enrichment
    agentic_plan = body.get("agentic_plan") or body.get("plan")
    agentic_plan_hash = (_canonical_inputs_hash(agentic_plan) if isinstance(agentic_plan, dict) else None)
    agentic_consent = body.get("consent") if isinstance(body.get("consent"), dict) else None

    # Fast in-process idempotency
    mem_key = f"ih:{input_hash}"
    mem_idemp_key = f"ik:{idempotency_key}" if idempotency_key else None
    if mem_idemp_key and mem_idemp_key in _IDEMP_CACHE:
        return {"run_id": _IDEMP_CACHE[mem_idemp_key], "status": "EXISTS"}, 200
    if mem_key in _IDEMP_CACHE:
        return {"run_id": _IDEMP_CACHE[mem_key], "status": "EXISTS"}, 200

    payload: dict | None = None
    status_code: int | None = None

    # Catalog idempotency (header, then hash)
    existing = _check_idempotency_catalog(catalog, input_hash, idempotency_key)
    if existing:
        _update_idemp_cache(mem_key, mem_idemp_key, existing["run_id"])  # type: ignore[arg-type]
        payload = {"run_id": existing["run_id"], "status": "EXISTS"}
        status_code = 200

    if payload is None:
        # Create QUEUED row + manifest
        from datetime import datetime
        from uuid import uuid4

        run_id = uuid4().hex
        created_at = datetime.now(UTC).isoformat()
        from backend.utils.paths import get_backtests_dir

        manifest_path = str((get_backtests_dir(run_id) / "run-manifest.json").resolve())

        creation = {
            "run_id": run_id,
            "dataset_id": dataset_id,  # type: ignore[arg-type]
            "strategy_id": strategy_id,  # type: ignore[arg-type]
            "params": params,
            "seed": seed,
            "slippage_fees": slippage_fees,
            "speed": speed,
            "created_at": created_at,
            "manifest_path": manifest_path,
            "input_hash": input_hash,
            "idempotency_key": idempotency_key,
            "agentic_plan": agentic_plan,
            "agentic_plan_hash": agentic_plan_hash,
            "agentic_consent": agentic_consent,
        }
        if strategies:
            try:
                creation["strategies"] = [
                    {"strategy_id": s.get("strategy_id"), "params": s.get("params") or {}}
                    for s in strategies
                    if isinstance(s, dict)
                ]
            except Exception:
                pass
        new_run_id, existed = _persist_queued_run_and_manifest(catalog, creation=creation)
        if existed:
            _update_idemp_cache(mem_key, mem_idemp_key, new_run_id)
            payload = {"run_id": new_run_id, "status": "EXISTS"}
            status_code = 200
        else:
            # Store in-memory idempotency keys for subsequent identical requests
            _update_idemp_cache(mem_key, mem_idemp_key, new_run_id)
            # Launch background process (non-blocking) to run and persist
            job_args = {
                "dataset_id": dataset_id,  # type: ignore[arg-type]
                "strategy_id": strategy_id,  # type: ignore[arg-type]
                "params": params,
                "seed": seed,
                "speed": speed,
                "slippage_fees": slippage_fees,
                "run_id": new_run_id,
                "from_date": run_from,
                "to_date": run_to,
            }
            if strategies:
                job_args["strategies"] = [
                    {"strategy_id": s.get("strategy_id"), "params": s.get("params") or {}}
                    for s in strategies
                    if isinstance(s, dict)
                ]
                # Also persist strategies into creation for manifest write
                try:
                    creation["strategies"] = job_args["strategies"]
                except Exception:
                    pass
            _enqueue_run_background(job_args=job_args)
            payload = {"run_id": new_run_id, "status": "QUEUED"}
            status_code = 202

    return payload, status_code  # type: ignore[return-value]
