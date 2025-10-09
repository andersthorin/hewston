"""Protocol for market data acquisition and access.

Implementations handle ingestion and ensuring datasets exist.
"""

from __future__ import annotations

from typing import Protocol


class MarketDataPort(Protocol):
    """Abstraction for ensuring symbol-year datasets are available."""

    def ensure_dataset(self, symbol: str, year: int) -> str:
        """Ensure dataset exists for symbol-year, returning dataset_id.

        Implementations may ingest, derive, and upsert into catalog.
        """
        ...
