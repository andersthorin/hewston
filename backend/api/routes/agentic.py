"""Agentic Mode routes: propose a plan and start runs (MVP).

Endpoints
- POST /agentic/propose_plan { from_date, to_date }
- POST /agentic/start { plan }
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from backend.services.agentic import propose_plan as propose_plan_svc
from backend.services.agentic import start_agentic_run as start_agentic_svc

router = APIRouter()
logger = logging.getLogger(__name__)
# Simple in-memory rate limiter for Agentic endpoints (MVP)
_RATE_BUCKETS: dict[str, list[float]] = {}


def _client_key(request: Request) -> str:
    # Prefer user identity header if present, fallback to IP
    uid = request.headers.get("X-User-Id") or request.headers.get("X-User")
    if uid:
        return f"user:{uid.strip()}"
    fwd = request.headers.get("x-forwarded-for")
    return (fwd or request.client.host or "unknown").split(",")[0].strip()


def _rate_limited(request: Request) -> bool:
    import os, time

    try:
        limit = int(os.getenv("AGENTIC_MAX_PER_MIN", "10"))
    except Exception:
        limit = 10
    key = _client_key(request)
    now = time.time()
    window = 60.0
    bucket = _RATE_BUCKETS.setdefault(key, [])
    # drop old
    while bucket and (now - bucket[0]) > window:
        bucket.pop(0)
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False



@router.post("/agentic/propose_plan")
async def propose_plan(request: Request):
    import os
    if os.getenv("AGENTIC_MODE_ENABLED", "1") not in ("1", "true", "TRUE", "yes", "on"):
        logger.info(json.dumps({"event":"agentic.denied","reason":"disabled"}))
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": "DISABLED", "message": "Agentic Mode is disabled"}},
        )
    if _rate_limited(request):
        logger.info(json.dumps({"event":"agentic.denied","reason":"rate_limited","key":_client_key(request)}))
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": {"code": "RATE_LIMIT", "message": "Too many requests"}},
        )
    try:
        raw = await request.body()
        body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "BAD_REQUEST", "message": "invalid JSON"}},
        )

    # Optional consent headers recorded for transparency
    consent_by = request.headers.get("X-Agentic-Consent-By")
    consent_at = request.headers.get("X-Agentic-Consent-At")
    if consent_by or consent_at:
        body["consent"] = {"by": consent_by, "at": consent_at}


    from_date = (body or {}).get("from_date") or (body or {}).get("run_from")
    to_date = (body or {}).get("to_date") or (body or {}).get("run_to")
    if not isinstance(from_date, str) or not isinstance(to_date, str):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "from_date and to_date are required (YYYY-MM-DD)",
                }
            },
        )

    plan = propose_plan_svc(from_date, to_date)
    # Structured log for propose
    try:
        logger.info(json.dumps({
            "event": "agentic.propose",
            "from": from_date,
            "to": to_date,
            "key": _client_key(request)
        }))
    except Exception:
        pass

    return JSONResponse(status_code=status.HTTP_200_OK, content=plan)


@router.post("/agentic/start")
async def start_agentic(request: Request):
    import os
    if os.getenv("AGENTIC_MODE_ENABLED", "1") not in ("1", "true", "TRUE", "yes", "on"):
        logger.info(json.dumps({"event":"agentic.denied","reason":"disabled"}))
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": {"code": "DISABLED", "message": "Agentic Mode is disabled"}},
        )
    if _rate_limited(request):
        logger.info(json.dumps({"event":"agentic.denied","reason":"rate_limited","key":_client_key(request)}))
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": {"code": "RATE_LIMIT", "message": "Too many requests"}},
        )
    # Structured log for start
    try:
        logger.info(json.dumps({
            "event": "agentic.start",
            "symbols": [s.get("symbol") for s in (plan.get("universe", {}).get("included") or [])],
            "strategy": ((plan.get("strategies") or [{}])[0]).get("strategy_id"),
            "key": _client_key(request)
        }))
    except Exception:
        pass

    try:
        raw = await request.body()
        body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "BAD_REQUEST", "message": "invalid JSON"}},
        )

    # Optional consent headers recorded for transparency
    consent_by = request.headers.get("X-Agentic-Consent-By")
    consent_at = request.headers.get("X-Agentic-Consent-At")
    if consent_by or consent_at:
        body["consent"] = {"by": consent_by, "at": consent_at}

    plan = (body or {}).get("plan") or body
    payload = start_agentic_svc(plan)

    # Service may return (error, code) tuple-like when bad input
    if isinstance(payload, tuple) and len(payload) == 2:
        data, code = payload  # type: ignore[misc]
        return JSONResponse(status_code=code, content=data)

    return JSONResponse(status_code=status.HTTP_200_OK, content=payload)

