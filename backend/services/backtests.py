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

# Backward-compatible naming: prefer 'backtest' over 'run'
# Keep legacy functions but expose backtest-named helpers for clarity

def get_backtest_service(backtest_id: str) -> Optional[dict]:
    return get_run_service(backtest_id)


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
    return list_runs_service(
        symbol=symbol,
        strategy_id=strategy_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
        order=order,
    )



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
    year = body.get("year")

    if not dataset_id:
        # Require either dataset_id or (symbol + year); attempt to derive year from dates when possible
        if symbol is not None and year is None:
            # Try to derive year from 'from' then 'to'
            source = from_date or to_date
            if isinstance(source, str) and len(source) >= 4 and source[:4].isdigit():
                try:
                    year = int(source[:4])
                except Exception:
                    year = None
        if symbol is None or year is None:
            return {"error": {"code": "BAD_REQUEST", "message": "Missing required parameter: dataset_id or (symbol + year)"}}, 400
        # Defer dataset materialization to the background worker; compute canonical id now
        dataset_id = f"{symbol}-{int(year)}-1m"

    catalog = get_catalog()

    # Ensure a placeholder dataset row exists to satisfy FK; background worker will materialize data
    if dataset_id and (symbol and year):
        try:
            from datetime import datetime, timezone as _tz
            catalog.upsert_dataset({
                "dataset_id": dataset_id,
                "symbol": symbol,
                "from_date": f"{int(year)}-01-01",
                "to_date": f"{int(year)}-12-31",
                "products": [],
                "raw_dbn": [],
                "bars_parquet": [],
                "bars_manifest_path": None,
                "generated_at": datetime.now(_tz.utc).isoformat(),
                "size_bytes": 0,
                "status": "BUILDING",
            })
        except Exception:
            # Best-effort; if this fails, create_run will fail FK and bubble up
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
