"""Agentic orchestrator: propose a plan and start runs within guardrails.

Scope: MVP for Epics 16/18/19/21
- propose_plan(from_date, to_date) -> PlanV1
- start_agentic_run(plan) -> { run_ids: [...] }

Universe discovery is file-system based under data/warehouse/quotes/venue=XNAS/symbol=*/date=*
Guardrails (MVP): coverage >= threshold (default 0.9)
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from backend.services.backtests import create_backtest_service


VENUE = "XNAS"
WAREHOUSE_QUOTES = Path("data/warehouse/quotes")


@dataclass(slots=True)
class PlanInputs:
    from_date: str
    to_date: str
    venue: str = VENUE
    max_symbols: int = 5
    coverage_threshold: float = 0.9


@dataclass(slots=True)
class SymbolCoverage:
    symbol: str
    coverage: float
    dates: list[str]
    reason: str | None = None


def _list_symbol_dirs(venue: str) -> list[Path]:
    base = WAREHOUSE_QUOTES / f"venue={venue}"
    if not base.exists():
        return []
    return sorted([p for p in base.iterdir() if p.is_dir() and p.name.startswith("symbol=")])


def _list_dates_for_symbol_dir(sym_dir: Path) -> list[str]:
    dates: list[str] = []
    for d in sorted(sym_dir.iterdir() if sym_dir.exists() else []):
        if d.is_dir() and d.name.startswith("date="):
            datestr = d.name.split("=", 1)[1]
            dates.append(datestr)
    return dates


def _daterange_list(from_date: str, to_date: str) -> list[str]:
    """Return list of trading days for coverage checks.

    MVP: use pandas BusinessDay frequency (Mon–Fri). This excludes weekends so
    multi-week/month ranges don't penalize symbols for market-closed days.
    Note: U.S. market holidays are not excluded in this MVP.
    """
    try:
        import pandas as pd  # type: ignore

        return (
            pd.bdate_range(pd.to_datetime(from_date), pd.to_datetime(to_date))
            .strftime("%Y-%m-%d")
            .tolist()
        )
    except Exception:
        # Fail-safe: single from_date only; callers handle low coverage accordingly
        return [from_date]


def _compute_coverage(symbol: str, all_dates: list[str], want_dates: list[str]) -> SymbolCoverage:
    have = set(all_dates)
    want = list(dict.fromkeys(want_dates))
    matched = sum(1 for d in want if d in have)
    cov = float(matched) / float(len(want) or 1)
    return SymbolCoverage(symbol=symbol, coverage=cov, dates=[d for d in want if d in have])


def discover_universe(inputs: PlanInputs) -> tuple[list[SymbolCoverage], list[SymbolCoverage]]:
    """Discover symbols and coverage.

    If UniverseV1 manifest exists, filter to its symbols; otherwise scan warehouse.
    """
    from backend.services.universe import load_universe

    included: list[SymbolCoverage] = []
    excluded: list[SymbolCoverage] = []
    want_dates = _daterange_list(inputs.from_date, inputs.to_date)

    u = load_universe()
    symbols: list[str]
    if u and u.symbols:
        symbols = list(dict.fromkeys([str(s) for s in u.symbols]))
    else:
        symbols = [p.name.split("=", 1)[1] for p in _list_symbol_dirs(inputs.venue)]

    # Build quick lookup of available dates from warehouse
    date_index: dict[str, list[str]] = {}
    if not u:
        # when scanning, we already have dirs
        for sym_dir in _list_symbol_dirs(inputs.venue):
            symbol = sym_dir.name.split("=", 1)[1]
            date_index[symbol] = _list_dates_for_symbol_dir(sym_dir)
    else:
        # Only fetch dates for requested symbols
        base = WAREHOUSE_QUOTES / f"venue={inputs.venue}"
        for symbol in symbols:
            sym_dir = base / f"symbol={symbol}"
            date_index[symbol] = _list_dates_for_symbol_dir(sym_dir)

    for symbol in symbols:
        dates = date_index.get(symbol, [])
        sc = _compute_coverage(symbol, dates, want_dates)
        if sc.coverage >= inputs.coverage_threshold:
            included.append(sc)
        else:
            sc.reason = "COVERAGE_LOW"
            excluded.append(sc)

    included.sort(key=lambda s: s.coverage, reverse=True)
    return included[: inputs.max_symbols], excluded


def get_strategy_set() -> list[dict[str, Any]]:
    """Return strategy specs for plan preview.

    MVP: include currently registered strategies from StrategyRegistry; do not import heavy deps.
    """
    from backend.strategies.strategy_factory import StrategyRegistry

    reg = StrategyRegistry()
    specs: list[dict[str, Any]] = []
    for sid in sorted(reg._registry.keys()):  # type: ignore[attr-defined]
        specs.append({"strategy_id": sid, "default_params": {}})
    return specs


def propose_plan(from_date: str, to_date: str) -> dict[str, Any]:
    inputs = PlanInputs(from_date=from_date, to_date=to_date)
    included, excluded = discover_universe(inputs)
    strategies = get_strategy_set()

    # Default bundling mode from env (backward compatible)
    import os as _os

    bundle_mode = _os.getenv("AGENTIC_DEFAULT_BUNDLE_MODE", "per_symbol").strip().lower()
    if bundle_mode not in ("per_symbol", "multi_symbol"):
        bundle_mode = "per_symbol"

    plan = {
        "version": 1,
        "inputs": asdict(inputs),
        "universe": {
            "included": [asdict(sc) for sc in included],
            "excluded": [asdict(sc) for sc in excluded],
        },
        "strategies": strategies,
        "guardrails": {
            "coverage_threshold": inputs.coverage_threshold,
        },
        "bundle_mode": bundle_mode,
        "notes": [
            "Bundling policy: default per-symbol. Set bundle_mode=multi_symbol to create a single portfolio run with all symbols\u00d7strategies.",
        ],
    }
    return plan


def start_agentic_run(plan: dict[str, Any]) -> dict[str, Any]:
    """Start runs from plan and return run_ids.

    Modes:
    - per_symbol (default): one run per symbol with multi-strategy inside each
    - multi_symbol: a single portfolio run with all symbols×strategies
    """
    from fastapi import status
    from backend.services.universe import load_universe, default_instrument_id

    uni = (plan or {}).get("universe") or {}
    strategies = (plan or {}).get("strategies") or []
    if not uni or not strategies:
        return {"error": {"code": "BAD_REQUEST", "message": "invalid or empty plan"}}, status.HTTP_400_BAD_REQUEST

    # Build multi-strategy set but keep first for compatibility with service validation
    strategy_id = (strategies[0] or {}).get("strategy_id") if strategies else None
    if not strategy_id:
        return {"error": {"code": "BAD_REQUEST", "message": "no strategy in plan"}}, status.HTTP_400_BAD_REQUEST

    inputs = (plan or {}).get("inputs") or {}
    from_date = inputs.get("from_date")
    to_date = inputs.get("to_date")
    venue = inputs.get("venue") or VENUE

    u = load_universe()

    # Determine bundling mode (env default for compatibility)
    import os

    bundle_mode = (plan or {}).get("bundle_mode") or os.getenv("AGENTIC_DEFAULT_BUNDLE_MODE", "per_symbol")
    bundle_mode = str(bundle_mode).strip().lower()
    if bundle_mode not in ("per_symbol", "multi_symbol"):
        bundle_mode = "per_symbol"

    # Optional budget cap for per_symbol mode
    try:
        max_runs = int(os.getenv("AGENTIC_PLAN_MAX_RUNS", "10"))
    except Exception:
        max_runs = 10

    included = list(uni.get("included") or [])

    # --- multi_symbol portfolio: create ONE run with all symbols×strategies ---
    if bundle_mode == "multi_symbol" and included:
        strategies_list = []
        for sc in included:
            symbol = sc.get("symbol")
            if not symbol:
                continue
            instrument_id = default_instrument_id(symbol, venue=venue, u=u)
            for s in strategies:
                sid = (s or {}).get("strategy_id")
                if not sid:
                    continue
                sp = dict((s or {}).get("default_params") or {})
                sp.setdefault("instrument_id", instrument_id)
                strategies_list.append({"strategy_id": sid, "params": sp})
        if not strategies_list:
            return {"error": {"code": "BAD_REQUEST", "message": "no strategies to run"}}, status.HTTP_400_BAD_REQUEST

        body = {
            "dataset_id": "XNAS-portfolio",
            "strategy_id": strategy_id,  # compat column
            "strategies": strategies_list,
            # Keep a representative symbol for legacy consumers (first included)
            "symbol": included[0].get("symbol"),
            "run_from": from_date,
            "run_to": to_date,
            "agentic_plan": plan,
            "params": {"instrument_id": default_instrument_id(included[0].get("symbol"), venue=venue, u=u) if included else None},
        }
        payload, code = create_backtest_service(body, idempotency_key=None)
        if code in (200, 201, 202) and isinstance(payload, dict) and payload.get("run_id"):
            return {"run_ids": [payload["run_id"]]}
        return {"run_ids": []}

    # --- per_symbol (default): one run per symbol ---
    run_ids: list[str] = []
    for idx, sc in enumerate(included):
        if idx >= max_runs:
            break
        symbol = sc.get("symbol")
        if not symbol:
            continue
        instrument_id = default_instrument_id(symbol, venue=venue, u=u)
        # Build strategies list with instrument_id injected
        strategies_list = []
        for s in strategies:
            sid = (s or {}).get("strategy_id")
            if not sid:
                continue
            sp = dict((s or {}).get("default_params") or {})
            sp.setdefault("instrument_id", instrument_id)
            strategies_list.append({"strategy_id": sid, "params": sp})
        body = {
            "strategy_id": strategy_id,  # compat
            "strategies": strategies_list,
            "symbol": symbol,
            "run_from": from_date,
            "run_to": to_date,
            "agentic_plan": plan,
            "params": {"instrument_id": instrument_id},
        }
        payload, code = create_backtest_service(body, idempotency_key=None)
        if code in (200, 201, 202) and isinstance(payload, dict):
            rid = payload.get("run_id")
            if rid:
                run_ids.append(rid)
    return {"run_ids": run_ids}

