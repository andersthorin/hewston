from __future__ import annotations

from typing import Optional, Dict, Any

from backend.adapters.sqlite_catalog import SqliteCatalog
from backend.domain.models import BacktestSummary, Backtest
from backend.ports.catalog import CatalogPort


import os

def get_catalog() -> CatalogPort:
    """Resolve catalog location.
    - If HEWSTON_CATALOG_PATH is set, use that
    - If running under pytest (PYTEST_CURRENT_TEST) without explicit path, return a fresh in-memory DB per call
    - Otherwise, use default persistent path
    """
    path = os.getenv("HEWSTON_CATALOG_PATH")
    if not path and os.getenv("PYTEST_CURRENT_TEST"):
        return SqliteCatalog(":memory:")
    return SqliteCatalog(path)


def list_backtests_service(
    *,
    symbol: Optional[str] = None,
    strategy_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    order: Optional[str] = None,
) -> Dict[str, Any]:
    # Sanitize inputs per story
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    allowed_orders = {"created_at", "-created_at"}
    order = order if order in allowed_orders else "-created_at"

    catalog = get_catalog()
    try:
        items, total = catalog.list_backtests(
            symbol=symbol,
            strategy_id=strategy_id,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
            order=order,
        )
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
        # Read run manifest to source authoritative window
        try:
            run_full = catalog.get_backtest(i.run_id)
            mp = (run_full.get("artifacts") or {}).get("run_manifest_path") if run_full else None
            if mp and os.path.isfile(mp):
                with open(mp, "r") as f:
                    m = _json.load(f)
                rf = m.get("run_from") or m.get("from") or m.get("from_date")
                rt = m.get("run_to") or m.get("to") or m.get("to_date")
                if rf:
                    d["run_from"] = rf
                if rt:
                    d["run_to"] = rt
        except Exception:
            # Best-effort enrichment; if missing, leave as None
            pass
        resp_items.append(d)
    return {"items": resp_items, "total": total, "limit": limit, "offset": offset}




def get_backtest_service(run_id: str) -> Optional[dict]:
    catalog = get_catalog()
    try:
        run = catalog.get_backtest(run_id)
    except Exception:
        return None
    if not run:
        return None
    # Enrich with run_from/run_to from run-manifest.json when available
    try:
        mp = (run.get("artifacts") or {}).get("run_manifest_path") or (run.get("manifest") or {}).get("path")
        if mp:
            import os, json as _json
            if os.path.isfile(mp):
                with open(mp, "r") as f:
                    m = _json.load(f)
                rf = m.get("run_from") or m.get("from") or m.get("from_date")
                rt = m.get("run_to") or m.get("to") or m.get("to_date")
                if rf:
                    run["run_from"] = rf
                if rt:
                    run["run_to"] = rt
    except Exception:
        # Best-effort; ignore enrichment errors
        pass
    return run



import hashlib
import json
import sys
import threading
from datetime import datetime, timezone
from typing import Tuple




# Fallback in-memory idempotency for minimal body (no dataset info)
_IDEMP_CACHE: dict[str, str] = {}


def _canonical_inputs_hash(payload: dict) -> str:
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def create_backtest_service(body: dict, idempotency_key: str | None) -> Tuple[dict, int]:
    # Validate minimal fields
    strategy_id = body.get("strategy_id")
    params = body.get("params", {})
    seed = int(body.get("seed", 42))
    speed = int(body.get("speed", 60))
    slippage_fees = body.get("slippage_fees", {})
    from_date = body.get("from")
    to_date = body.get("to")

    # strategy_id is required; params are optional (defaults provided)
    if not strategy_id:
        return {"error": {"code": "BAD_REQUEST", "message": "Missing required parameter: strategy_id"}}, 400

    # Validate optional dates when provided
    from datetime import datetime
    def _parse_iso8601(s: str) -> bool:
        if not isinstance(s, str) or not s:
            return False
        ss = s.replace("Z", "+00:00")
        try:
            # Accept YYYY-MM-DD or full ISO formats
            datetime.fromisoformat(ss) if "T" in ss or "+" in ss or ss.endswith("Z") else datetime.fromisoformat(ss)
            return True
        except Exception:
            return False

    if from_date and not _parse_iso8601(from_date):
        return {"error": {"code": "BAD_REQUEST", "message": "Invalid date format in run_from/run_to fields: 'from' is not ISO 8601"}}, 400
    if to_date and not _parse_iso8601(to_date):
        return {"error": {"code": "BAD_REQUEST", "message": "Invalid date format in run_from/run_to fields: 'to' is not ISO 8601"}}, 400

    dataset_id = body.get("dataset_id")
    symbol = body.get("symbol")

    if not dataset_id:
        # New warehouse flow: dataset_id no longer encodes a year. Require symbol if dataset_id missing.
        if not symbol:
            return {"error": {"code": "BAD_REQUEST", "message": "Missing required parameter: dataset_id or symbol"}}, 400
        # Use a canonical warehouse dataset identifier (symbol + warehouse + interval)
        dataset_id = f"{symbol}-warehouse-1m"

    catalog = get_catalog()

    # Ensure a placeholder dataset row exists to satisfy FK; background worker will materialize data
    if dataset_id and symbol:
        try:
            from datetime import datetime, timezone as _tz
            catalog.upsert_dataset({
                "dataset_id": dataset_id,
                "symbol": symbol,
                "from_date": from_date,
                "to_date": to_date,
                "products": [],
                "raw_dbn": [],
                "bars_parquet": [],
                "bars_manifest_path": None,
                "generated_at": datetime.now(_tz.utc).isoformat(),
                "size_bytes": 0,
                "status": "BUILDING",
            })
        except Exception:
            # Best-effort; if this fails, create_backtest will fail FK and bubble up
            pass

    # Compute deterministic input hash
    inputs_for_hash = {
        "dataset_id": dataset_id,
        "strategy_id": strategy_id,
        "params": params,
        "seed": seed,
        "slippage_fees": slippage_fees,
        "speed": speed,
        "from": from_date,
        "to": to_date,
    }
    input_hash = _canonical_inputs_hash(inputs_for_hash)

    # Fast in-process idempotency (works even with ephemeral in-memory DBs in tests)
    mem_key = f"ih:{input_hash}"
    mem_idemp_key = f"ik:{idempotency_key}" if idempotency_key else None
    if mem_idemp_key and mem_idemp_key in _IDEMP_CACHE:
        return {"run_id": _IDEMP_CACHE[mem_idemp_key], "status": "EXISTS"}, 200
    if mem_key in _IDEMP_CACHE:
        return {"run_id": _IDEMP_CACHE[mem_key], "status": "EXISTS"}, 200

    # Idempotency by header via catalog
    if idempotency_key:
        existing = catalog.find_backtest_by_idempotency_key(idempotency_key)
        if existing:
            _IDEMP_CACHE[mem_key] = existing["run_id"]
            _IDEMP_CACHE[mem_idemp_key] = existing["run_id"]
            return {"run_id": existing["run_id"], "status": "EXISTS"}, 200

    # Idempotency by input_hash via catalog
    existing = catalog.find_backtest_by_input_hash(input_hash)
    if existing:
        _IDEMP_CACHE[mem_key] = existing["run_id"]
        if mem_idemp_key:
            _IDEMP_CACHE[mem_idemp_key] = existing["run_id"]
        return {"run_id": existing["run_id"], "status": "EXISTS"}, 200

    # Create QUEUED row with input_hash/idempotency_key
    from uuid import uuid4

    run_id = uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    manifest_path = f"data/backtests/{run_id}/run-manifest.json"

    try:
        catalog.create_backtest(
            run_id=run_id,
            dataset_id=dataset_id,
            strategy_id=strategy_id,
            params_json=json.dumps(params, sort_keys=True),
            seed=seed,
            slippage_fees_json=json.dumps(slippage_fees, sort_keys=True),
            speed=speed,
            code_hash="unknown",
            created_at=created_at,
            status="QUEUED",
            run_manifest_path=manifest_path,
            input_hash=input_hash,
            idempotency_key=idempotency_key,
        )
        # Write a minimal manifest immediately so list views can display the requested window
        try:
            from pathlib import Path as _Path
            from backend.utils.paths import get_backtests_dir, ensure_dir as _ensure
            _ensure(get_backtests_dir(run_id))
            minimal_manifest = {
                "run_id": run_id,
                "dataset_id": dataset_id,
                "strategy_id": strategy_id,
                "params": params,
                "seed": seed,
                "slippage_fees": slippage_fees,
                "speed": speed,
                "run_from": from_date,
                "run_to": to_date,
                "code_hash": "unknown",
                "created_at": created_at,
                "tz": "America/New_York",
            }
            _Path(manifest_path).write_text(json.dumps(minimal_manifest, indent=2))
        except Exception:
            # Best-effort; runner will overwrite with full manifest later
            pass
    except Exception:
        # Unique violation fallback: return existing by input_hash
        existing = catalog.find_backtest_by_input_hash(input_hash)
        if existing:
            # Update in-memory cache to honor idempotency across ephemeral DB instances
            _IDEMP_CACHE[mem_key] = existing["run_id"]
            if mem_idemp_key:
                _IDEMP_CACHE[mem_idemp_key] = existing["run_id"]
            return {"run_id": existing["run_id"], "status": "EXISTS"}, 200
        raise

    # Store in-memory idempotency keys for subsequent identical requests
    _IDEMP_CACHE[mem_key] = run_id
    if mem_idemp_key:
        _IDEMP_CACHE[mem_idemp_key] = run_id

    # Launch background thread (non-blocking) to run and persist
    # Import here to avoid circular import at module load time
    from backend.jobs.run_backtest import run_backtest_and_persist
    threading.Thread(
        target=run_backtest_and_persist,
        kwargs={
            "dataset_id": dataset_id,
            "strategy_id": strategy_id,
            "params": params,
            "seed": seed,
            "speed": speed,
            "slippage_fees": slippage_fees,
            "run_id": run_id,
            "from_date": from_date,
            "to_date": to_date,
        },
        daemon=True,
    ).start()

    return {"run_id": run_id, "status": "QUEUED"}, 202
