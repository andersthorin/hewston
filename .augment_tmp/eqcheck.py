import json
from pathlib import Path
import polars as pl

run_id = "6ee2d2ded3134c75aa8cd57dd109183f"
base = Path("data/backtests") / run_id
mp = base / "metrics.json"
eqp = base / "equity.parquet"
print("metrics.json exists:", mp.exists())
print("equity.parquet exists:", eqp.exists())
if mp.exists():
    mj = json.loads(mp.read_text())
    tr = mj.get("total_return")
    end_bal = mj.get("ending_balance") or mj.get("ending_equity")
    print("total_return:", tr)
    if isinstance(tr, (int, float)):
        expected = 10000.0 * (1.0 + float(tr))
        print("expected_final_equity:", round(expected, 2))
    print("ending_balance_from_metrics:", end_bal)
if eqp.exists():
    df = pl.read_parquet(eqp)
    print("equity rows:", df.height)
    if df.height > 0:
        last = df[-1]
        try:
            last_val = float(last["value"])
        except Exception:
            last_val = None
        print("last_equity_value:", round(last_val, 2) if last_val is not None else None)
        print("first_rows_sample:", df.head(3).to_dicts())
