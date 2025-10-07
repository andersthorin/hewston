"""
Materialize UI bars from Quotes + Trades aggregates

Outputs:
  data/warehouse/bars/mid_1min/venue=XNAS/symbol={SYM}/date=YYYY-MM-DD/bars.parquet
  data/warehouse/bars/mid_1h/  venue=XNAS/symbol={SYM}/date=YYYY-MM-DD/bars.parquet

Schema:
  t: timestamp[ns, tz=UTC]  # bucket start
  o,h,l,c: float64          # from MID (quotes)
  v: int64 (sum trades volume)
  n: int64 (trade count)
  vw: float64 (trades VWAP)
  provider: utf8            # 'quotes+trades'
  rth: bool (for 1min; optional for 1h)
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd


def _quotes_base() -> Path:
    return Path("data/warehouse/quotes").resolve()


def _trades_base() -> Path:
    return Path("data/warehouse/trades_agg").resolve()


def _bars_base() -> Path:
    return Path("data/warehouse/bars").resolve()


def _glob_quotes(symbol: str, date_str: str, venue: str = "XNAS") -> Path:
    return (
        _quotes_base()
        / f"venue={venue}"
        / f"symbol={symbol}"
        / f"date={date_str}"
        / "quotes.parquet"
    )


def _glob_trades(symbol: str, date_str: str, timeframe: str, venue: str = "XNAS") -> Path:
    return (
        _trades_base()
        / timeframe
        / f"venue={venue}"
        / f"symbol={symbol}"
        / f"date={date_str}"
        / "agg.parquet"
    )


def _out_path(symbol: str, date_str: str, timeframe: str, venue: str = "XNAS") -> Path:
    return (
        _bars_base()
        / f"mid_{timeframe}"
        / f"venue={venue}"
        / f"symbol={symbol}"
        / f"date={date_str}"
        / "bars.parquet"
    )


def _derive_mid_ohlc_from_quotes(quotes: pd.DataFrame, freq: str) -> pd.DataFrame:
    # quotes: ts, bid_px, ask_px
    mid = (pd.to_numeric(quotes["bid_px"]) + pd.to_numeric(quotes["ask_px"])) / 2.0
    s = pd.Series(mid.values, index=pd.to_datetime(quotes["ts"], utc=True)).sort_index()
    ohlc = s.resample(freq).ohlc()
    ohlc = ohlc.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c"})
    ohlc["t"] = ohlc.index
    return ohlc[["t", "o", "h", "l", "c"]].reset_index(drop=True)


def _merge_trades(bars: pd.DataFrame, trades: pd.DataFrame | None) -> pd.DataFrame:
    if trades is None or trades.empty:
        bars["v"] = 0
        bars["n"] = 0
        bars["vw"] = 0.0
        return bars
    # trades: t, v, n, vw
    out = bars.merge(trades, on="t", how="left")
    out["v"] = out["v"].fillna(0).astype("int64")
    out["n"] = out["n"].fillna(0).astype("int64")
    out["vw"] = out["vw"].fillna(0.0).astype("float64")
    return out


def _flag_rth(bars_1m: pd.DataFrame) -> pd.DataFrame:
    # 09:30-16:00 America/New_York corresponds to 13:30-20:00 UTC (no DST handling here; acceptable for pilot)
    t = pd.to_datetime(bars_1m["t"], utc=True)
    hours = t.dt.hour
    mins = t.dt.minute
    total = hours * 60 + mins
    rth = (total >= 14 * 60 - 30) & (total < 20 * 60)  # 13:30-19:59 inclusive
    bars_1m["rth"] = rth.astype(bool)
    return bars_1m


def materialize_for_date(symbol: str, date_str: str, venue: str = "XNAS") -> tuple[Path, Path]:
    q_path = _glob_quotes(symbol, date_str, venue)
    if not q_path.exists():
        raise FileNotFoundError(f"Quotes parquet not found: {q_path}")
    quotes = pd.read_parquet(q_path)

    # 1min bars
    bars_1m = _derive_mid_ohlc_from_quotes(quotes, "1min")
    t1m_path = _glob_trades(symbol, date_str, "1min", venue)
    t1m = pd.read_parquet(t1m_path) if t1m_path.exists() else None
    ui_1m = _merge_trades(bars_1m, t1m)
    ui_1m = _flag_rth(ui_1m)
    ui_1m["provider"] = "quotes+trades"

    # 1h bars
    bars_1h = _derive_mid_ohlc_from_quotes(quotes, "1h")
    t1h_path = _glob_trades(symbol, date_str, "1h", venue)
    t1h = pd.read_parquet(t1h_path) if t1h_path.exists() else None
    ui_1h = _merge_trades(bars_1h, t1h)
    ui_1h["provider"] = "quotes+trades"

    # Write
    p1 = _out_path(symbol, date_str, "1min", venue)
    p2 = _out_path(symbol, date_str, "1h", venue)
    p1.parent.mkdir(parents=True, exist_ok=True)
    p2.parent.mkdir(parents=True, exist_ok=True)
    ui_1m.to_parquet(p1, index=False)
    ui_1h.to_parquet(p2, index=False)
    return p1, p2


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Materialize UI bars from Quotes + Trades aggregates")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--venue", default="XNAS")
    args = ap.parse_args()

    p = materialize_for_date(args.symbol, args.date, args.venue)
    print("written:", p)
