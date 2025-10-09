#!/usr/bin/env python3
"""
Debug script to run a backtest with full logging and analyze results.
"""
import sys
import json
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("debug_backtest.log", mode="w"),
    ],
)

# Set specific loggers to DEBUG for more detail
logging.getLogger("strategy.events").setLevel(logging.INFO)
logging.getLogger("strategy.orders").setLevel(logging.INFO)
logging.getLogger("strategy.fills").setLevel(logging.INFO)
logging.getLogger("nautilus.runner").setLevel(logging.INFO)
logging.getLogger("nautilus.metrics").setLevel(logging.INFO)
logging.getLogger("backtest.job").setLevel(logging.INFO)

print("=" * 80)
print("BACKTEST DEBUG SESSION")
print("=" * 80)
print()

# Import after logging is configured
from backend.jobs.run_backtest import run_backtest_and_persist
import polars as pl

# Run backtest
print("Starting backtest...")
print()

try:
    result = run_backtest_and_persist(
        req={
            "dataset_id": "googl_oct_2024",
            "strategy_id": "sma_crossover",
            "params": {"instrument_id": "GOOGL.XNAS", "fast": 20, "slow": 50},
            "from_date": "2024-10-01",
            "to_date": "2024-10-10",
            "seed": 42,
        }
    )

    print()
    print("=" * 80)
    print("BACKTEST COMPLETED")
    print("=" * 80)
    print()
    print(json.dumps(result, indent=2))
    print()

    # Analyze the results
    if result.get("status") == "DONE":
        run_id = result["run_id"]
        base_path = Path(f"data/backtests/{run_id}")

        print("=" * 80)
        print("ANALYZING RESULTS")
        print("=" * 80)
        print()

        # Check metrics.json
        metrics_path = base_path / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                metrics = json.load(f)
            print("📊 METRICS (metrics.json):")
            print(json.dumps(metrics, indent=2))
            print()
        else:
            print("❌ metrics.json not found!")
            print()

        # Check equity.parquet
        equity_path = base_path / "equity.parquet"
        if equity_path.exists():
            df = pl.read_parquet(equity_path)
            print(f"📈 EQUITY CURVE (equity.parquet):")
            print(f"   Rows: {len(df)}")
            print(f"   Start: ${df['value'][0]:.2f}")
            print(f"   End: ${df['value'][-1]:.2f}")
            print(f"   Min: ${df['value'].min():.2f}")
            print(f"   Max: ${df['value'].max():.2f}")

            unique_values = df["value"].unique()
            if len(unique_values) == 1:
                print(f"   ⚠️  EQUITY IS FLAT at ${unique_values[0]:.2f}")
            else:
                print(f"   ✅ Equity varies ({len(unique_values)} unique values)")
            print()
        else:
            print("❌ equity.parquet not found!")
            print()

        # Check orders.parquet
        orders_path = base_path / "orders.parquet"
        if orders_path.exists():
            df = pl.read_parquet(orders_path)
            print(f"📋 ORDERS (orders.parquet):")
            print(f"   Total: {len(df)}")
            if len(df) > 0:
                print(f"   BUY: {len(df.filter(pl.col('side') == 'BUY'))}")
                print(f"   SELL: {len(df.filter(pl.col('side') == 'SELL'))}")
                print(f"   Sample:")
                print(df.head(3))
            print()
        else:
            print("❌ orders.parquet not found!")
            print()

        # Check fills.parquet
        fills_path = base_path / "fills.parquet"
        if fills_path.exists():
            df = pl.read_parquet(fills_path)
            print(f"💰 FILLS (fills.parquet):")
            print(f"   Total: {len(df)}")
            if len(df) == 0:
                print(f"   ❌ NO FILLS RECORDED!")
                print(f"   This means on_order_filled() was never called!")
            else:
                print(f"   ✅ Fills recorded!")
                print(f"   BUY: {len(df.filter(pl.col('side') == 'BUY'))}")
                print(f"   SELL: {len(df.filter(pl.col('side') == 'SELL'))}")
                print(f"   Sample:")
                print(df.head(3))
            print()
        else:
            print("❌ fills.parquet not found!")
            print()

        print("=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)
        print()

        # Diagnose the issue
        has_orders = orders_path.exists() and len(pl.read_parquet(orders_path)) > 0
        has_fills = fills_path.exists() and len(pl.read_parquet(fills_path)) > 0
        equity_flat = False
        if equity_path.exists():
            df = pl.read_parquet(equity_path)
            equity_flat = len(df["value"].unique()) == 1

        if has_orders and not has_fills:
            print("❌ PROBLEM: Orders submitted but no fills recorded")
            print("   → on_order_filled() callback is not being called")
            print("   → Check logs above for 'on_order_filled CALLED' messages")
            print("   → Check logs for order event types (OrderFilled, OrderAccepted, etc.)")
            print()

        if equity_flat:
            print("❌ PROBLEM: Equity curve is flat")
            print("   → Strategy's manual tracking never updated")
            print("   → OR Nautilus portfolio access is working")
            print("   → Check logs for 'Extracted from Nautilus portfolio' messages")
            print()

        if metrics.get("total_return") == 0.0:
            print("❌ PROBLEM: Metrics show 0% return")
            print("   → Metrics extraction fell back to flat equity curve")
            print("   → Check logs for 'Failed to extract from Nautilus' messages")
            print()

        print("Check debug_backtest.log for full details")
        print()

except Exception as e:
    print()
    print("=" * 80)
    print("BACKTEST FAILED")
    print("=" * 80)
    print()
    print(f"Error: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
    print()
    print("Check debug_backtest.log for full details")
