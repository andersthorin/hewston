from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class StreamFrame:
    t: str  # "frame"
    ts: str  # ISO-8601 UTC string
    ohlc: Optional[Dict[str, Any]]
    orders: List[Dict[str, Any]]
    equity: Optional[Dict[str, Any]]  # { ts, value }
    dropped: int = 0


class Control:
    PLAY = "play"
    PAUSE = "pause"
    SEEK = "seek"
    SPEED = "speed"

