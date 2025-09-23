#!/usr/bin/env bash
set -euo pipefail
# Measure REST latencies for GET /backtests and GET /backtests/{id}
# Usage: ./scripts/bench_rest.sh [host] [count]
#  host: default http://127.0.0.1:8000
#  count: default 200
HOST=${1:-http://127.0.0.1:8000}
COUNT=${2:-200}

# Ensure one run_id is available; if none, fall back to /backtests only
RUN_ID=$(curl -s "$HOST/backtests?limit=1" | awk -F '"' '/run_id/ {print $4; exit}')

measure() {
  URL=$1
  for i in $(seq 1 $COUNT); do
    T=$(curl -o /dev/null -s -w "%{time_total}\n" "$URL")
    echo "$T"
  done
}

percentiles() {
  PCTS="$1" # space-separated percentiles e.g. "0.5 0.95"
  awk -v pcts="$PCTS" '
    {a[NR]=$1}
    END{
      n=asort(a)
      split(pcts,ps," ")
      for(i in ps){
        p=ps[i]
        idx=int(p*n); if(idx<1) idx=1; if(idx>n) idx=n;
        printf("p%.0f=%.3f ", p*100, a[idx]*1000)
      }
      printf("\n")
    }
  '
}

echo "[bench_rest] GET /backtests x$COUNT"
measure "$HOST/backtests" | percentiles "0.5 0.95"

if [[ -n "$RUN_ID" ]]; then
  echo "[bench_rest] GET /backtests/$RUN_ID x$COUNT"
  measure "$HOST/backtests/$RUN_ID" | percentiles "0.5 0.95"
else
  echo "[bench_rest] No run_id available; skipping GET /backtests/{id}"
fi

