from __future__ import annotations

import os
import sys
from typing import Optional

from backend.jobs.ingest import ingest_databento
from backend.jobs.derive import derive_bars
from backend.adapters.databento import ensure_dataset

# Optional Typer interface; fall back to argparse if Typer isn't installed
try:
    import typer  # type: ignore
except Exception:  # pragma: no cover
    typer = None  # type: ignore


def _run_data(symbol: str, year: int, force: bool) -> int:
    try:
        sizes = ingest_databento(symbol=symbol, year=year, force=force)
        total = sum(sizes.values())
        print(f"[ingest] completed: products={list(sizes.keys())} total_bytes={total}")
        manifest = derive_bars(symbol=symbol, year=year, force=force)
        print(f"[derive] completed: outputs={list(manifest.get('output_hashes',{}).keys())}")
        dsid = ensure_dataset(symbol=symbol, year=year, force=force)
        print(f"[catalog] dataset_id={dsid}")
        return 0
    except SystemExit as e:
        # Bubble up with proper exit code and message
        print(f"[ingest] ERROR: {e}")
        return 2


if typer is not None:
    app = typer.Typer(no_args_is_help=True, add_completion=False)

    @app.command(name="data")
    def data_cmd(
        symbol: str = typer.Option(..., "--symbol", help="Ticker symbol, e.g., AAPL"),
        year: int = typer.Option(..., "--year", help="Year, e.g., 2023"),
        force: bool = typer.Option(False, "--force/--no-force", help="Re-download even if present"),
    ) -> None:
        code = _run_data(symbol, year, force)
        raise typer.Exit(code)

    @app.command(name="backtest")
    def backtest_cmd(
        symbol: str = typer.Option(None, "--symbol"),
        year: int = typer.Option(None, "--year"),
        dataset_id: str = typer.Option(None, "--dataset-id"),
        run_id: str = typer.Option(None, "--run-id"),
        strategy_id: str = typer.Option("sma_crossover", "--strategy-id"),
        param: list[str] = typer.Option([], "--param"),  # e.g., --param fast=20 --param slow=50
        seed: int = typer.Option(42, "--seed"),
        speed: int = typer.Option(60, "--speed"),
        force: bool = typer.Option(False, "--force/--no-force"),
        from_date: str = typer.Option(None, "--from", help="unused in stub"),
        to_date: str = typer.Option(None, "--to", help="unused in stub"),
    ) -> None:
        # Ensure dataset exists if not provided
        if not dataset_id:
            if symbol is None or year is None:
                print("[backtest] ERROR: provide --dataset-id or (--symbol and --year)")
                raise typer.Exit(2)
            dataset_id = ensure_dataset(symbol=symbol, year=year, force=force)
        # Parse params list into dict
        p: dict[str, str] = {}
        for kv in param:
            if "=" in kv:
                k, v = kv.split("=", 1)
                p[k] = v
        # Run and persist artifacts
        from backend.jobs.run_backtest import run_backtest_and_persist

        out = run_backtest_and_persist(
            dataset_id=dataset_id,
            strategy_id=strategy_id,
            params=p,
            seed=seed,
            speed=speed,
            slippage_fees={},
            run_id=run_id,
        )
        print(f"[backtest] run_id={out['run_id']} duration_ms={out['duration_ms']}")
        raise typer.Exit(0)

    @app.command(name="retention")
    def retention_cmd(
        keep_latest: int = typer.Option(100, "--keep-latest"),
        max_age_days: int = typer.Option(None, "--max-age"),
        apply: bool = typer.Option(False, "--apply"),
    ) -> None:
        from backend.jobs.retention import retention_main
        code = retention_main(keep_latest=keep_latest, max_age_days=max_age_days, apply=apply)
        raise typer.Exit(code)



def main_argv(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if typer is not None:
        # Delegate to Typer if present
        try:
            # Build a Typer app on the fly to parse argv
            from typer import Exit  # type: ignore
            # Emulate: app(prog_name=..., args=argv)
            # But simpler: detect subcommand and options
            # If this execution path is reached, just print help
            print("Use: python -m backend.jobs.cli data --symbol SYMBOL --year YEAR [--force]")
            return 0
        except Exception:
            pass
    # Fallback: argparse minimal parser
    import argparse

    parser = argparse.ArgumentParser(prog="hewston-jobs")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_data = sub.add_parser("data", help="Ingest Databento DBN (stub)")
    p_data.add_argument("--symbol", required=True)
    p_data.add_argument("--year", type=int, required=True)
    p_data.add_argument("--force", action="store_true")

    ns = parser.parse_args(argv)
    if ns.cmd == "data":
        return _run_data(ns.symbol, ns.year, ns.force)
    return 1


if __name__ == "__main__":
    raise SystemExit(main_argv())

