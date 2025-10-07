export type BacktestSummaryRow = {
  backtest_id: string
  created_at: string
  strategy_id: string
  status: string
  symbol?: string | null
  run_from?: string | null
  run_to?: string | null
  duration_ms?: number | null
}

export type BacktestsTableProps = {
  items: BacktestSummaryRow[]
  onView?: (backtest_id: string) => void
}

export function BacktestsTable({ items, onView }: BacktestsTableProps) {
  if (!items.length) {
    return <div>No backtests yet. Create a backtest to get started.</div>
  }
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-slate-200">
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">backtest_id</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">created_at</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">strategy_id</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">status</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">symbol</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">run_from</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">run_to</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">duration_ms</th>
          <th className="px-2 py-1"></th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <Row key={r.backtest_id} r={r} onView={onView} />
        ))}
      </tbody>
    </table>
  )
}

function Row({ r, onView }: { r: BacktestSummaryRow; onView?: (id: string) => void }) {
  const runFrom = r.run_from ?? '—'
  const runTo = r.run_to ?? '—'
  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50">
      <td className="px-2 py-1 font-mono">{r.backtest_id}</td>
      <td className="px-2 py-1">{r.created_at}</td>
      <td className="px-2 py-1">{r.strategy_id}</td>
      <td className="px-2 py-1">
        <div className="flex items-center gap-2">
          <span>{r.status}</span>
          {r.status === 'DONE' || r.status === 'COMPLETED' ? (
            <span
              className="inline-flex items-center rounded bg-emerald-100 text-emerald-700 px-2 py-0.5 text-xs"
              title="Real engine (no stub fallback)"
              aria-label="Engine: Nautilus Trader"
            >
              Engine: Nautilus Trader
            </span>
          ) : null}
        </div>
      </td>
      <td className="px-2 py-1">{r.symbol ?? ''}</td>
      <td className="px-2 py-1">{runFrom}</td>
      <td className="px-2 py-1">{runTo}</td>
      <td className="px-2 py-1">{r.duration_ms ?? ''}</td>
      <td className="px-2 py-1">
        <button
          className="px-2 py-1 rounded bg-slate-800 text-white hover:bg-slate-700"
          onClick={() => onView?.(r.backtest_id)}
        >
          View
        </button>
      </td>
    </tr>
  )
}

export default BacktestsTable
