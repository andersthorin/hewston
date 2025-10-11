export type BacktestSummaryRow = {
  backtest_id: string
  created_at: string
  strategy_id: string
  status: string
  symbol?: string | null
  run_from?: string | null
  run_to?: string | null
  duration_ms?: number | null
  total_return?: number | null
  max_drawdown?: number | null
  sharpe_ratio?: number | null
  win_rate?: number | null
  // Portfolio surfacing (optional)
  instruments_count?: number | null
  strategies_count?: number | null
  is_portfolio?: boolean | null
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
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">total_return</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">max_drawdown</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">sharpe</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">win_rate</th>
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
  const s = String(r.status || '').toUpperCase()
  const isQueued = s === 'QUEUED'
  const isRunning = s === 'RUNNING'
  const isDone = s === 'DONE' || s === 'COMPLETED'
  const isError = s === 'ERROR' || s === 'FAILED'
  const isTerminal = isDone || isError
  const label = isQueued
    ? 'Queued'
    : isRunning
      ? 'Running'
      : isDone
        ? 'Done'
        : isError
          ? 'Error'
          : s
  const badgeClass = isQueued
    ? 'bg-slate-200 text-slate-700'
    : isRunning
      ? 'bg-blue-100 text-blue-700'
      : isDone
        ? 'bg-emerald-100 text-emerald-700'
        : isError
          ? 'bg-rose-100 text-rose-700'
          : 'bg-slate-100 text-slate-700'
  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50">
      <td className="px-2 py-1 font-mono">{r.backtest_id}</td>
      <td className="px-2 py-1">{r.created_at}</td>
      <td className="px-2 py-1">{r.strategy_id}</td>
      <td className="px-2 py-1">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded px-2 py-0.5 text-xs ${badgeClass}`}
            aria-live="polite"
          >
            {label}
          </span>
          {isDone ? (
            <span
              className="inline-flex items-center rounded bg-emerald-100 text-emerald-700 px-2 py-0.5 text-xs"
              title="Real engine (no stub fallback)"
              aria-label="Engine: Nautilus Trader"
            >
              Engine: Nautilus Trader
            </span>
          ) : null}
          {((r.instruments_count ?? 0) > 1 || r?.is_portfolio) ? (
            <span
              className="inline-flex items-center rounded bg-indigo-100 text-indigo-700 px-2 py-0.5 text-xs"
              title="Portfolio run"
              aria-label="Portfolio run"
            >
              {`Portfolio (${Math.max(1, r.instruments_count || 0)} syms${typeof r.strategies_count === 'number' && r.strategies_count > 0 ? ", " + r.strategies_count + " strats" : ''})`}
            </span>
          ) : null}
        </div>
      </td>
      <td className="px-2 py-1">{((r.instruments_count ?? 0) > 1 || r?.is_portfolio) ? `Portfolio (${Math.max(1, r.instruments_count || 0)} symbols)` : (r.symbol ?? '')}</td>
      <td className="px-2 py-1">{runFrom}</td>
      <td className="px-2 py-1">{runTo}</td>
      <td className="px-2 py-1">{r.duration_ms ?? ''}</td>
      {/* Metrics columns */}
      <td className="px-2 py-1">
        {isTerminal && typeof r.total_return === 'number' ? (
          <span className={r.total_return >= 0 ? 'text-emerald-700' : 'text-rose-700'}>
            {(r.total_return * 100).toFixed(2)}%
          </span>
        ) : (
          <span>—</span>
        )}
      </td>
      <td className="px-2 py-1">
        {isTerminal && typeof r.max_drawdown === 'number' ? (
          <span className={r.max_drawdown <= 0 ? 'text-rose-700' : 'text-slate-700'}>
            {(r.max_drawdown * 100).toFixed(2)}%
          </span>
        ) : (
          <span>—</span>
        )}
      </td>
      <td className="px-2 py-1">
        {isTerminal && typeof r.sharpe_ratio === 'number' ? (
          r.sharpe_ratio.toFixed(2)
        ) : (
          <span>—</span>
        )}
      </td>
      <td className="px-2 py-1">
        {isTerminal && typeof r.win_rate === 'number' ? (
          `${(r.win_rate * 100).toFixed(1)}%`
        ) : (
          <span>—</span>
        )}
      </td>
      <td className="px-2 py-1">
        {isTerminal ? (
          <button
            className="px-2 py-1 rounded bg-slate-800 text-white hover:bg-slate-700"
            onClick={() => onView?.(r.backtest_id)}
          >
            View
          </button>
        ) : (
          <span className="text-slate-400 text-xs" aria-label="View available when complete">
            —
          </span>
        )}
      </td>
    </tr>
  )
}

export default BacktestsTable
