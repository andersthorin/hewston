"""
Trades DBN -> per-minute and per-hour aggregates

Partitions:
  data/warehouse/trades_agg/1min/venue=XNAS/symbol={SYM}/date=YYYY-MM-DD/agg.parquet
  data/warehouse/trades_agg/1h/  venue=XNAS/symbol={SYM}/date=YYYY-MM-DD/agg.parquet

Schema (Parquet):
  t: timestamp[ns, tz=UTC]  # bucket start
  v: int64                  # volume (sum size)
  n: int64                  # trade count
  vw: float64               # VWAP within bucket (sum px*size / sum size)
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

try:
    from databento import DBNStore  # type: ignore
except Exception:
    DBNStore = None  # type: ignore


def _base() -> Path:
    return Path("data/warehouse/trades_agg").resolve()


def _out_path(symbol: str, date_str: str, timeframe: str, venue: str = "XNAS") -> Path:
    return (
        _base()
        / timeframe
        / f"venue={venue}"
        / f"symbol={symbol}"
        / f"date={date_str}"
        / "agg.parquet"
    )


def _bucket(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    # df has columns: ts_event, price, size
    ts = pd.to_datetime(df["ts_event"], unit="ns", utc=True)
    price = pd.to_numeric(df["price"], errors="coerce")
    size = pd.to_numeric(df["size"], errors="coerce")
    # Build without implicit reindex to handle duplicate timestamps gracefully
    s = pd.DataFrame(
        {
            "price": price.to_numpy(),
            "size": size.to_numpy(),
        },
        index=pd.Index(ts.to_numpy(), name="ts"),
    ).dropna()
    # Resample to freq
    vol = s["size"].resample(freq).sum().fillna(0)
    cnt = s["size"].resample(freq).count().fillna(0)
    # VWAP: sum(price*size)/sum(size) where vol > 0
    notional = (s["price"] * s["size"]).resample(freq).sum().fillna(0)
    vwap = (notional / vol.where(vol > 0)).fillna(0.0).astype("float64")
    out = pd.DataFrame(
        {"t": vol.index, "v": vol.astype("int64"), "n": cnt.astype("int64"), "vw": vwap}
    )
    return out


def aggregate_trades_dbn_to_parquet(
    dbn_file: Path, instrument_id: int, symbol: str, venue: str = "XNAS"
) -> tuple[Path, Path]:
    if DBNStore is None:
        raise ImportError("databento is required to aggregate trades DBN files")
    store = DBNStore.from_file(str(dbn_file))
    try:
        df = store.to_df(schema="trades")
    except TypeError:
        df = store.to_df()

    sdf = df[df["instrument_id"] == instrument_id]
    if sdf.empty:
        raise ValueError(f"No trades for instrument_id={instrument_id} in {dbn_file}")

    # Date partition key
    date_str: str | None = None
    for tok in str(dbn_file).split("/")[-1].split(".")[0].split("-"):
        if tok.isdigit() and len(tok) == 8:
            date_str = f"{tok[0:4]}-{tok[4:6]}-{tok[6:8]}"
            break
    if not date_str:
        date_str = str(pd.to_datetime(sdf["ts_event"].iloc[0], unit="ns", utc=True).date())

    out_1m = _bucket(sdf, "1min")
    out_1h = _bucket(sdf, "1h")

    p1 = _out_path(symbol, date_str, timeframe="1min", venue=venue)
    p2 = _out_path(symbol, date_str, timeframe="1h", venue=venue)
    p1.parent.mkdir(parents=True, exist_ok=True)
    p2.parent.mkdir(parents=True, exist_ok=True)
    out_1m.to_parquet(p1, index=False)
    out_1h.to_parquet(p2, index=False)
    return p1, p2


def aggregate_many(
    dbn_files: Iterable[Path], instrument_id: int, symbol: str, venue: str = "XNAS"
) -> list[tuple[Path, Path]]:
    written: list[tuple[Path, Path]] = []
    for f in dbn_files:
        try:
            written.append(aggregate_trades_dbn_to_parquet(f, instrument_id, symbol, venue))
        except Exception as e:
            print(f"[trades_aggregate] failed {f}: {e}")
    return written


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Aggregate trades DBN -> per-minute/hour parquet")
    ap.add_argument("dbn", nargs="+", help="DBN file(s)")
    ap.add_argument("--instrument-id", type=int, required=True)
    ap.add_argument("--symbol", type=str, required=True)
    ap.add_argument("--venue", type=str, default="XNAS")
    args = ap.parse_args()

    out = aggregate_many([Path(p) for p in args.dbn], args.instrument_id, args.symbol, args.venue)
    print("written:", len(out))
