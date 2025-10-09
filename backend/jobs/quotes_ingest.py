"""TBBO DBN -> canonical QuoteTicks parquet (partitioned).

Partitions:
  data/warehouse/quotes/venue=XNAS/symbol={SYM}/date=YYYY-MM-DD/quotes.parquet

Schema (Parquet):
  ts: timestamp[ns, tz=UTC]
  instrument_id: int64
  bid_px: float64
  ask_px: float64
  bid_sz: float32 (optional)
  ask_sz: float32 (optional)
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

try:
    from databento import DBNStore  # type: ignore
except Exception:  # pragma: no cover
    DBNStore = None  # type: ignore



# Filename token length for YYYYMMDD
DATE_TOKEN_LEN = 8

def _warehouse_base() -> Path:
    return Path("data/warehouse/quotes").resolve()


def _out_path(symbol: str, date_str: str, venue: str = "XNAS") -> Path:
    return (
        _warehouse_base()
        / f"venue={venue}"
        / f"symbol={symbol}"
        / f"date={date_str}"
        / "quotes.parquet"
    )


def ingest_tbbo_dbn_to_parquet(
    dbn_file: Path, instrument_id: int, symbol: str, venue: str = "XNAS"
) -> Path:
    """Ingest a single TBBO DBN file to partitioned Parquet for one instrument.

    Args:
        dbn_file: path to Databento TBBO DBN (.dbn.zst)
        instrument_id: numeric instrument ID to filter
        symbol: symbol string (e.g., AAPL)
        venue: venue string (default XNAS)

    Returns:
        Path to written parquet file.
    """
    if DBNStore is None:
        raise ImportError("databento is required to ingest TBBO DBN files")

    store = DBNStore.from_file(str(dbn_file))
    try:
        df = store.to_df(schema="tbbo")
    except TypeError:
        df = store.to_df()

    sdf = df[df["instrument_id"] == instrument_id]
    if sdf.empty:
        raise ValueError(f"No rows for instrument_id={instrument_id} in {dbn_file}")

    # Normalize columns (level 0 depth)
    required = ["ts_event", "bid_px_00", "ask_px_00"]
    for col in required:
        if col not in sdf.columns:
            raise ValueError(f"Missing TBBO column {col} in {dbn_file}")

    ts = pd.to_datetime(sdf["ts_event"], unit="ns", utc=True)
    pdf = (
        pd.DataFrame(
            {
                "ts": ts,
                "instrument_id": pd.to_numeric(
                    sdf["instrument_id"], errors="coerce", downcast=None
                ),
                "bid_px": pd.to_numeric(sdf["bid_px_00"], errors="coerce"),
                "ask_px": pd.to_numeric(sdf["ask_px_00"], errors="coerce"),
                "bid_sz": pd.to_numeric(sdf.get("bid_sz_00", 0.0), errors="coerce").astype(
                    "float32"
                ),
                "ask_sz": pd.to_numeric(sdf.get("ask_sz_00", 0.0), errors="coerce").astype(
                    "float32"
                ),
            }
        )
        .dropna(subset=["ts", "bid_px", "ask_px"])
        .sort_values("ts")
    )

    # Derive partition key from filename if possible (expects ...YYYYMMDD...)
    date_str: str | None = None
    for tok in str(dbn_file).split("/")[-1].split(".")[0].split("-"):
        if tok.isdigit() and len(tok) == DATE_TOKEN_LEN:
            date_str = f"{tok[0:4]}-{tok[4:6]}-{tok[6:8]}"
            break
    if not date_str:
        # Fallback to first timestamp date
        date_str = str(pdf["ts"].dt.date.min())

    out_path = _out_path(symbol, date_str, venue=venue)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Use pyarrow via pandas to_parquet; preserve timestamp tz
    pdf.to_parquet(out_path, index=False)
    return out_path


def ingest_many(
    dbn_files: Iterable[Path], instrument_id: int, symbol: str, venue: str = "XNAS"
) -> list[Path]:
    """Ingest multiple DBN files; continue on errors and return written parquet paths."""
    written: list[Path] = []
    for f in dbn_files:
        try:
            p = ingest_tbbo_dbn_to_parquet(f, instrument_id, symbol, venue)
            written.append(p)
        except Exception as e:
            # Best-effort; continue
            print(f"[quotes_ingest] failed {f}: {e}")
    return written


if __name__ == "__main__":  # simple CLI
    import argparse

    ap = argparse.ArgumentParser(description="Ingest TBBO DBN -> Quotes Parquet")
    ap.add_argument("dbn", nargs="+", help="DBN file(s)")
    ap.add_argument("--instrument-id", type=int, required=True)
    ap.add_argument("--symbol", type=str, required=True)
    ap.add_argument("--venue", type=str, default="XNAS")
    args = ap.parse_args()

    paths = ingest_many([Path(p) for p in args.dbn], args.instrument_id, args.symbol, args.venue)
    print("written:", len(paths))
