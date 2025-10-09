import BacktestsTable, { type BacktestSummaryRow } from '../BacktestsTable'

// Legacy wrapper: adapts older RunSummary shape to BacktestsTable's BacktestSummaryRow
// Keeps tests and any legacy callers working while we standardize on backtests
export type RunsTableProps = {
  items: Array<any>
  onView?: (backtest_id: string) => void
}

export default function RunsTable({ items, onView }: RunsTableProps) {
  const adapted: BacktestSummaryRow[] = items.map((r: any, idx: number) => ({
    backtest_id: r.backtest_id ?? r.run_id ?? String(idx),
    created_at: r.created_at,
    strategy_id: r.strategy_id,
    status: r.status,
    symbol: r.symbol ?? null,
    run_from: r.run_from ?? null,
    run_to: r.run_to ?? null,
    duration_ms: r.duration_ms ?? null,
    total_return: r.total_return ?? null,
    max_drawdown: r.max_drawdown ?? null,
    sharpe_ratio: r.sharpe_ratio ?? null,
    win_rate: r.win_rate ?? null,
  }))
  return <BacktestsTable items={adapted} onView={onView} />
}
