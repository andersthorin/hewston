from __future__ import annotations

from typing import Protocol, Optional, List, Dict, Any
from backend.domain.models import RunSummary, Dataset


class CatalogPort(Protocol):
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        ...

    def list_runs(
        self,
        *,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        order: str = "-created_at",
    ) -> tuple[List[RunSummary], int]:
        """Return (items, total)."""
        ...

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        ...

    # Stubs for later
    def upsert_dataset(self, dataset: Dict[str, Any]) -> None:
        raise NotImplementedError

    def create_run(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError

    def set_run_status(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

