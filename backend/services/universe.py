"""UniverseV1 loading and helpers (Epic 18).

- Loads optional UniverseV1 manifest from data/universe/universe.json
- Provides symbol list and default instrument_id mapping (e.g., AAPL -> AAPL.XNAS)
- Minimal validation only (MVP)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

UNIVERSE_PATH = Path("data/universe/universe.json")


@dataclass(slots=True)
class UniverseV1:
    as_of: str
    symbols: list[str]
    instrument_map: dict[str, str] | None = None
    venue: str | None = None


def _validate_universe(payload: dict[str, Any]) -> UniverseV1 | None:
    try:
        as_of = str(payload.get("as_of"))
        symbols = list(payload.get("symbols") or [])
        if not symbols:
            return None
        instrument_map = payload.get("instrument_map") or None
        venue = payload.get("venue") or None
        return UniverseV1(as_of=as_of, symbols=[str(s) for s in symbols], instrument_map=instrument_map, venue=venue)
    except Exception:
        return None


def load_universe() -> UniverseV1 | None:
    try:
        if not UNIVERSE_PATH.exists():
            return None
        data = json.loads(UNIVERSE_PATH.read_text() or "{}")
        return _validate_universe(data)
    except Exception:
        return None


def default_instrument_id(symbol: str, *, venue: str = "XNAS", u: UniverseV1 | None = None) -> str:
    if u and isinstance(u.instrument_map, dict):
        val = u.instrument_map.get(symbol)
        if isinstance(val, str) and val:
            return val
    return f"{symbol}.{venue}"

