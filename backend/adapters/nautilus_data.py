from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import polars as pl

CATALOG_PATH = Path("data/catalog.sqlite")


def _get_dataset_row(dataset_id: str) -> Optional[dict]:
    import sqlite3

    if not CATALOG_PATH.exists():
        return None
    with sqlite3.connect(CATALOG_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,)
        ).fetchone()
        return dict(row) if row else None


def _resolve_bars_path(row: dict) -> Optional[Path]:
    import json

    try:
        files = json.loads(row.get("bars_parquet_json", "[]"))
        # Strict: only accept explicit bars_1Min.parquet entries
        for p in files:
            p_str = str(p)
            if p_str.endswith("bars_1Min.parquet"):
                path = Path(p_str)
                if path.exists():
                    return path
        return None
    except Exception:
        return None


@dataclass
class BarsWindow:
    from_date: str | None = None
    to_date: str | None = None


class ParquetDataAdapter:
    """Load 1m OHLCV bars (Polars) and optionally convert to Nautilus types.

    Conversion to Nautilus objects is only attempted when nautilus-trader is installed.
    """

    def load_bars(self, *, dataset_id: str, window: BarsWindow | None = None) -> pl.DataFrame:
        row = _get_dataset_row(dataset_id)
        if not row:
            raise SystemExit(f"dataset not found: {dataset_id}")
        bars_path = _resolve_bars_path(row)
        if not bars_path or not Path(bars_path).exists():
            raise SystemExit(f"bars parquet missing for dataset: {dataset_id}")

        df = pl.read_parquet(str(bars_path))
        # Accept both new schema ('t') and legacy ('ts')
        if "ts" not in df.columns and "t" in df.columns:
            df = df.rename({"t": "ts"})
        if "ts" not in df.columns:
            raise SystemExit("bars parquet missing required timestamp column ('t' or 'ts')")
        df = df.sort("ts")
        # Ensure price column exists
        if "c" not in df.columns:
            raise SystemExit("bars parquet missing close column 'c'")
        # Optional inclusive windowing
        if window and (window.from_date or window.to_date):
            from datetime import datetime

            def _parse(d: str, end: bool = False):
                if not d:
                    return None
                return datetime.fromisoformat(d + ("T23:59:59+00:00" if end else "T00:00:00+00:00"))

            start_dt = _parse(window.from_date or "")
            end_dt = _parse(window.to_date or "", end=True)
            if start_dt:
                df = df.filter(pl.col("ts") >= pl.lit(start_dt))
            if end_dt:
                df = df.filter(pl.col("ts") <= pl.lit(end_dt))
        return df

    @staticmethod
    def dataset_to_instrument_id(dataset_id: str) -> str:
        symbol = dataset_id.split("-")[0].upper() if "-" in dataset_id else dataset_id.upper()
        return f"{symbol}.XNAS"  # MVP default venue

    def convert_to_nautilus(self, *, bars_df: pl.DataFrame, instrument_id: str):
        """Convert Polars bars to Nautilus Bar list using BarDataWrangler.

        Returns list[Bar]. Requires nautilus-trader to be installed.
        """
        # Lazy imports to avoid hard dependency at import time
        import pandas as pd  # type: ignore
        try:
            from datetime import timedelta
            from nautilus_trader.model.data import BarType, BarSpecification
            from nautilus_trader.model.identifiers import InstrumentId
            from nautilus_trader.model.instruments import Equity
            from nautilus_trader.model.enums import PriceType, AggregationSource
            from nautilus_trader.persistence.wranglers import BarDataWrangler
        except Exception as e:  # pragma: no cover - only when package missing
            raise ImportError(
                "nautilus-trader not installed. Install it to enable real engine path."
            ) from e

        # Pandas DataFrame with tz-aware UTC index named 'timestamp'
        pdf = bars_df.rename({"ts": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}).to_pandas()
        pdf.set_index("timestamp", inplace=True)

        # Build instrument and bar type (1-minute MID, EXTERNAL)
        instr_id = InstrumentId.from_str(instrument_id)
        # Minimal Equity instrument (fields not required by wrangler)
        instr = Equity.from_dict({
            "id": instrument_id,
            "raw_symbol": instrument_id.split(".")[0],
            "symbol": instrument_id.split(".")[0],
            "asset_class": "EQUITY",
            "price_precision": 2,
            "price_increment": "0.01",
            "size_precision": 0,
            "size_increment": "1",
            "multiplier": "1",
            "lot_size": "1",
            "quote_currency": "USD",
            "currency": "USD",
            "ts_event": 0,
            "ts_init": 0,
            "info": {"name": instrument_id},
        })
        spec = BarSpecification.from_timedelta(timedelta(minutes=1), PriceType.MID)
        bar_type = BarType(instr_id, spec, AggregationSource.EXTERNAL)
        wrangler = BarDataWrangler(bar_type=bar_type, instrument=instr)
        bars = wrangler.process(pdf)
        return bars

    def create_data_engine(self, bars) -> "DataEngine":  # type: ignore[name-defined]
        from nautilus_trader.backtest.data_engine import DataEngine  # type: ignore

        engine = DataEngine()
        engine.add_data(bars)
        return engine

