#!/usr/bin/env python3
"""
Backfill Quotes Warehouse + UI bars for a date range and list of symbols.

- For each (symbol, date):
  1) TBBO DBN -> QuoteTicks parquet (quotes_ingest.py)
  2) Trades DBN -> 1m/1h aggregates (trades_aggregate.py)
  3) Materialize MID bars 1m/1h (materialize_bars.py)

Features:
- Resumable: skips work if data/warehouse/bars/mid_1min/.../bars.parquet already exists
- Parallel: configurable max workers (default 4)
- Progress reporting to terminal

Example:
  ./.venv/bin/python scripts/backfill_warehouse.py \
    --start 2024-09-20 --end 2025-09-19 \
    --symbols AAPL MSFT GOOGL TSLA NVDA \
    --venue XNAS --max-workers 4
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import os
import sys
import time
from pathlib import Path
from typing import Iterable, List, Tuple
import subprocess

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / ".venv" / "bin" / "python")

INSTRUMENT_IDS = {
    "AAPL": 38,
    "MSFT": 10888,
    "GOOGL": 7152,
    "TSLA": 16244,
    "NVDA": 11667,
}

RAW_TBBO = REPO / "data" / "raw" / "databento" / "tbbo"
RAW_TRADES = REPO / "data" / "raw" / "databento" / "trades"
WAREHOUSE = REPO / "data" / "warehouse"


def date_range(start: dt.date, end: dt.date) -> Iterable[dt.date]:
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def out_bar_path(symbol: str, venue: str, d: dt.date) -> Path:
    return (
        WAREHOUSE
        / "bars"
        / "mid_1min"
        / f"venue={venue}"
        / f"symbol={symbol}"
        / f"date={d:%Y-%m-%d}"
        / "bars.parquet"
    )


def raw_paths_for_date(d: dt.date) -> Tuple[Path, Path]:
    ymd = d.strftime("%Y%m%d")
    tbbo = RAW_TBBO / f"xnas-itch-{ymd}.tbbo.dbn.zst"
    trades = RAW_TRADES / f"xnas-itch-{ymd}.trades.dbn.zst"
    return tbbo, trades


def run_cmd(cmd: list[str]) -> int:
    """Run command streaming output; return exit code."""
    try:
        proc = subprocess.Popen(cmd, cwd=str(REPO))
        return proc.wait()
    except KeyboardInterrupt:
        return 130


def process_task(
    symbol: str, venue: str, d: dt.date, iid: int, quiet: bool = False
) -> Tuple[str, str, str]:
    """Process a single (symbol, date). Returns (status, symbol, date_str).
    status in {'ok','skip','missing','error'}
    """
    date_str = d.strftime("%Y-%m-%d")
    outp = out_bar_path(symbol, venue, d)
    if outp.exists():
        if not quiet:
            print(f"[SKIP] {symbol} {date_str} bars already exist: {outp}")
        return ("skip", symbol, date_str)

    tbbo, trades = raw_paths_for_date(d)
    if not tbbo.exists() or not trades.exists():
        print(
            f"[MISS] {symbol} {date_str} raw missing: tbbo={tbbo.exists()} trades={trades.exists()}"
        )
        return ("missing", symbol, date_str)

    # 1) Quotes ingest
    cmd1 = [
        PY,
        "backend/jobs/quotes_ingest.py",
        str(tbbo),
        "--instrument-id",
        str(iid),
        "--symbol",
        symbol,
        "--venue",
        venue,
    ]
    # 2) Trades aggregate
    cmd2 = [
        PY,
        "backend/jobs/trades_aggregate.py",
        str(trades),
        "--instrument-id",
        str(iid),
        "--symbol",
        symbol,
        "--venue",
        venue,
    ]
    # 3) Materialize bars
    cmd3 = [
        PY,
        "backend/jobs/materialize_bars.py",
        "--symbol",
        symbol,
        "--date",
        date_str,
        "--venue",
        venue,
    ]

    print(f"[RUN ] {symbol} {date_str} → quotes_ingest")
    rc = run_cmd(cmd1)
    if rc != 0:
        print(f"[ERR ] {symbol} {date_str} quotes_ingest rc={rc}")
        return ("error", symbol, date_str)

    print(f"[RUN ] {symbol} {date_str} → trades_aggregate")
    rc = run_cmd(cmd2)
    if rc != 0:
        print(f"[ERR ] {symbol} {date_str} trades_aggregate rc={rc}")
        return ("error", symbol, date_str)

    print(f"[RUN ] {symbol} {date_str} → materialize_bars")
    rc = run_cmd(cmd3)
    if rc != 0:
        print(f"[ERR ] {symbol} {date_str} materialize_bars rc={rc}")
        return ("error", symbol, date_str)

    print(f"[DONE] {symbol} {date_str}")
    return ("ok", symbol, date_str)


def build_tasks(
    symbols: List[str], start: dt.date, end: dt.date, venue: str
) -> list[tuple[str, dt.date, int, str]]:
    tasks: list[tuple[str, dt.date, int, str]] = []
    for sym in symbols:
        iid = INSTRUMENT_IDS.get(sym)
        if iid is None:
            print(f"[WARN] Unknown instrument id for symbol {sym}, skipping")
            continue
        for d in date_range(start, end):
            tasks.append((sym, d, iid, venue))
    return tasks


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"])
    p.add_argument("--venue", default="XNAS")
    p.add_argument("--max-workers", type=int, default=4)
    args = p.parse_args(argv)

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    tasks = build_tasks(args.symbols, start, end, args.venue)
    total = len(tasks)
    if total == 0:
        print("No tasks to process.")
        return 0

    print(
        f"Backfill start: symbols={args.symbols} dates={args.start}..{args.end} venue={args.venue} tasks={total}"
    )
    ok = err = skip = miss = done = 0
    t0 = time.time()

    # Submit tasks
    with cf.ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        futs = []
        for sym, d, iid, venue in tasks:
            futs.append(ex.submit(process_task, sym, venue, d, iid))
        for fut in cf.as_completed(futs):
            status, sym, date_str = fut.result()
            done += 1
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            elif status == "missing":
                miss += 1
            else:
                err += 1
            pct = int((done / total) * 100)
            elapsed = time.time() - t0
            sys.stdout.write(
                f"\r[PROG] {pct:3d}% {done}/{total} ok={ok} skip={skip} miss={miss} err={err} elapsed={elapsed:0.0f}s"
            )
            sys.stdout.flush()
    print()  # newline after progress
    print(
        f"Backfill finished: ok={ok} skip={skip} miss={miss} err={err} total={total} elapsed={time.time()-t0:0.1f}s"
    )
    return 0 if err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
