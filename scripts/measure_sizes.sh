#!/usr/bin/env bash
set -euo pipefail
# Summarize storage footprint of derived data and backtest artifacts.
# Usage: ./scripts/measure_sizes.sh [data_dir]
#  data_dir: defaults to ./data
ROOT=${1:-data}

human() {
  local kb=$1
  if (( kb > 1024*1024 )); then echo "$((kb/1024/1024)) GiB"; 
  elif (( kb > 1024 )); then echo "$((kb/1024)) MiB"; 
  else echo "${kb} KiB"; fi
}

sum_dir_kb() {
  local path=$1
  if [ -d "$path" ]; then du -sk "$path" | awk '{print $1}'; else echo 0; fi
}

derived_kb=$(sum_dir_kb "$ROOT/derived")
backtests_kb=$(sum_dir_kb "$ROOT/backtests")
raw_kb=$(sum_dir_kb "$ROOT/raw")

printf "derived: %s\n" "$(human "$derived_kb")"
printf "backtests: %s\n" "$(human "$backtests_kb")"
printf "raw: %s\n" "$(human "$raw_kb")"

# Per-run breakdown (top 10 by size)
if [ -d "$ROOT/backtests" ]; then
  echo "per-run (top 10):"
  du -sk "$ROOT/backtests"/* 2>/dev/null | sort -nr | head -n 10 | awk '{kb=$1; sub(/.*\//, "", $2); print $2, kb" KiB"}'
fi

