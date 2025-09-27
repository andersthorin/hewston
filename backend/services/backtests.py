from __future__ import annotations

from typing import Optional, Dict, Any

from backend.adapters.sqlite_catalog import SqliteCatalog
from backend.domain.models import RunSummary, Run
from backend.ports.catalog import CatalogPort


import os

def get_catalog() -> CatalogPort:
    # Use persistent catalog by default; override with HEWSTON_CATALOG_PATH if set
    # Passing None lets SqliteCatalog default to data/catalog.sqlite
    return SqliteCatalog(os.getenv("HEWSTON_CATALOG_PATH"))


def list_runs_service(
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
        items, total = catalog.list_runs(
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
            run_full = catalog.get_run(i.run_id)
            mp = (run_full.get("artifacts") or {}).get("run_manifest_path") if run_full else None
            if mp and os.path.isfile(mp):
                with open(mp, "r") as f:
                    m = _json.load(f)
                rf = m.get("from") or m.get("from_date")
                rt = m.get("to") or m.get("to_date")
                if rf:
                    d["run_from"] = rf
                if rt:
                    d["run_to"] = rt
        except Exception:
            # Best-effort enrichment; if missing, leave as None
            pass
        resp_items.append(d)
    return {"items": resp_items, "total": total, "limit": limit, "offset": offset}


def get_run_service(run_id: str) -> Optional[dict]:
    catalog = get_catalog()
    try:
        run = catalog.get_run(run_id)
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
                rf = m.get("from") or m.get("from_date")
                rt = m.get("to") or m.get("to_date")
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

from backend.adapters.databento import ensure_dataset
from backend.jobs.run_backtest import run_backtest_and_persist


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

    if not isinstance(params, dict) or not strategy_id:
        return {"error": {"code": "BAD_REQUEST", "message": "missing strategy_id/params"}}, 400

    dataset_id = body.get("dataset_id")
    symbol = body.get("symbol")
    year = body.get("year")

    if not dataset_id:
        if symbol is None or year is None:
            # Stub fallback (maintain earlier behavior for minimal body)
            if idempotency_key:
                if idempotency_key in _IDEMP_CACHE:
                    return {"run_id": _IDEMP_CACHE[idempotency_key], "status": "EXISTS"}, 200
                fake_run_id = f"stub-{__import__('uuid').uuid4().hex[:8]}"
                _IDEMP_CACHE[idempotency_key] = fake_run_id
                return {"run_id": fake_run_id, "status": "QUEUED"}, 202
            return {"error": {"code": "BAD_REQUEST", "message": "provide dataset_id or (symbol, year)"}}, 400
        # Ensure dataset exists (idempotent)
        dataset_id = ensure_dataset(symbol, int(year), force=False)

    catalog = get_catalog()

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

    # Idempotency by header
    if idempotency_key:
        existing = catalog.find_run_by_idempotency_key(idempotency_key)
        if existing:
            return {"run_id": existing["run_id"], "status": "EXISTS"}, 200

    # Idempotency by input_hash
    existing = catalog.find_run_by_input_hash(input_hash)
    if existing:
        return {"run_id": existing["run_id"], "status": "EXISTS"}, 200

    # Create QUEUED row with input_hash/idempotency_key
    from uuid import uuid4

    run_id = uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    manifest_path = f"data/backtests/{run_id}/run-manifest.json"

    try:
        catalog.create_run(
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
    except Exception:
        # Unique violation fallback: return existing by input_hash
        existing = catalog.find_run_by_input_hash(input_hash)
        if existing:
            return {"run_id": existing["run_id"], "status": "EXISTS"}, 200
        raise

    # Launch background thread (non-blocking) to run and persist
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
