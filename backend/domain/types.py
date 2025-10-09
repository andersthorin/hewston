"""Lightweight domain types for streaming and control messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StreamFrame:
    """Frame sent during playback streaming."""

    t: str  # "frame"
    ts: str  # ISO-8601 UTC string
    ohlc: dict[str, Any] | None
    orders: list[dict[str, Any]]
    equity: dict[str, Any] | None  # { ts, value }
    metrics: dict[str, float] | None = None  # E11: per-frame running metrics
    dropped: int = 0
    total_frames: int | None = None  # optional total number of frames for this stream


class Control:
    """Control message types for playback commands."""

    PLAY = "play"
    PAUSE = "pause"
    SEEK = "seek"
    SPEED = "speed"
