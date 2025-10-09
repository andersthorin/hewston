"""CLI for data ingest and backtest helpers (Typer if available, else argparse)."""

from __future__ import annotations

import sys

from backend.jobs.ingest import ingest_databento

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

        return 0
    except SystemExit as e:
        # Bubble up with proper exit code and message
        print(f"[ingest] ERROR: {e}")
        return 2


if typer is not None:
    app = typer.Typer(no_args_is_help=True, add_completion=False)

    # Define Option singletons to avoid B008 in default args
    OPT_SYMBOL_DATA = typer.Option(..., "--symbol", help="Ticker symbol, e.g., AAPL")
    OPT_YEAR_DATA = typer.Option(..., "--year", help="Year, e.g., 2023")
    OPT_FORCE_DATA = typer.Option(False, "--force/--no-force", help="Re-download even if present")

    OPT_SYMBOL_OPT = typer.Option(None, "--symbol")
    OPT_YEAR_OPT = typer.Option(None, "--year")
    OPT_DATASET_ID = typer.Option(None, "--dataset-id")
    OPT_RUN_ID = typer.Option(None, "--run-id")
    OPT_STRATEGY_ID = typer.Option("sma_crossover", "--strategy-id")
    OPT_PARAM = typer.Option([], "--param")  # e.g., --param fast=20 --param slow=50
    OPT_SEED = typer.Option(42, "--seed")
    OPT_SPEED = typer.Option(60, "--speed")
    OPT_FORCE_OPT = typer.Option(False, "--force/--no-force")
    OPT_FROM = typer.Option(None, "--from", help="unused in stub")
    OPT_TO = typer.Option(None, "--to", help="unused in stub")

    OPT_KEEP_LATEST = typer.Option(100, "--keep-latest")
    OPT_MAX_AGE = typer.Option(None, "--max-age")
    OPT_APPLY = typer.Option(False, "--apply")

    @app.command(name="data")
    def data_cmd(
        symbol: str = OPT_SYMBOL_DATA,
        year: int = OPT_YEAR_DATA,
        force: bool = OPT_FORCE_DATA,
    ) -> None:
        """Ingest Databento data (stub) and exit with appropriate code."""
        code = _run_data(symbol, year, force)
        raise typer.Exit(code)

    @app.command(name="backtest")
    def backtest_cmd(  # noqa: PLR0913 - CLI command intentionally exposes multiple options
        symbol: str = OPT_SYMBOL_OPT,
        year: int = OPT_YEAR_OPT,
        dataset_id: str = OPT_DATASET_ID,
        run_id: str = OPT_RUN_ID,
        strategy_id: str = OPT_STRATEGY_ID,
        param: list[str] = OPT_PARAM,  # e.g., --param fast=20 --param slow=50
        seed: int = OPT_SEED,
        speed: int = OPT_SPEED,
        force: bool = OPT_FORCE_OPT,
        from_date: str = OPT_FROM,
        to_date: str = OPT_TO,
    ) -> None:
        """Create and run a backtest, persisting artifacts; prints run_id and duration."""
        # Require dataset_id explicitly (no implicit dataset creation)
        if not dataset_id:
            print("[backtest] ERROR: provide --dataset-id (implicit dataset creation removed)")
            raise typer.Exit(2)
        # Parse params list into dict
        p: dict[str, str] = {}
        for kv in param:
            if "=" in kv:
                k, v = kv.split("=", 1)
                p[k] = v
        # Run and persist artifacts
        from backend.jobs.run_backtest import run_backtest_and_persist

        out = run_backtest_and_persist(
            req={
                "dataset_id": dataset_id,
                "strategy_id": strategy_id,
                "params": p,
                "seed": seed,
                "speed": speed,
                "slippage_fees": {},
                "run_id": run_id,
                "from_date": from_date,
                "to_date": to_date,
            }
        )
        print(f"[backtest] run_id={out['run_id']} duration_ms={out['duration_ms']}")
        raise typer.Exit(0)

    @app.command(name="retention")
    def retention_cmd(
        keep_latest: int = OPT_KEEP_LATEST,
        max_age_days: int = OPT_MAX_AGE,
        apply: bool = OPT_APPLY,
    ) -> None:
        """Apply retention policy; optionally delete when --apply is set."""
        from backend.jobs.retention import retention_main

        code = retention_main(keep_latest=keep_latest, max_age_days=max_age_days, apply=apply)
        raise typer.Exit(code)


def main_argv(argv: list[str] | None = None) -> int:
    """Entry point used by `python -m backend.jobs.cli` and tests."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if typer is not None:
        # Delegate to Typer if present

        try:
            # Build a Typer app on the fly to parse argv

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
