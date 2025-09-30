import React from 'react'

export type MetricsSummaryProps = {
  metrics?: Partial<{
    total_return: number
    sharpe_ratio: number
    max_drawdown: number
    win_rate: number
    profit_factor: number
    total_trades: number
  }>
  equity?: Array<{ ts: string; value: number }> | null
  loading?: boolean
}

function formatPercent(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  try {
    return `${(v * 100).toFixed(1)}%`
  } catch {
    return '—'
  }
}

function formatRatio(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  try {
    return Number(v).toFixed(digits)
  } catch {
    return '—'
  }
}

function formatInt(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  try {
    return `${Math.round(Number(v))}`
  } catch {
    return '—'
  }
}

function formatCurrency(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  try {
    return `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  } catch {
    return '—'
  }
}

const metricDefs: Array<{
  key: keyof NonNullable<MetricsSummaryProps['metrics']>
  label: string
  formatter: (v: number | null | undefined) => string
  title?: string
}> = [
  { key: 'total_return', label: 'Total return', formatter: formatPercent, title: 'End-to-start equity change' },
  { key: 'win_rate', label: 'Win rate', formatter: formatPercent, title: 'Winning trades / total trades' },
  { key: 'max_drawdown', label: 'Max drawdown', formatter: formatPercent, title: 'Peak-to-trough equity drawdown' },
  { key: 'sharpe_ratio', label: 'Sharpe', formatter: (v) => formatRatio(v, 2), title: 'Return / volatility (unitless)' },
  { key: 'profit_factor', label: 'Profit factor', formatter: (v) => formatRatio(v, 2), title: 'Gross profit / gross loss' },
  { key: 'total_trades', label: 'Trades', formatter: formatInt, title: 'Total executed trades' },
]

function getCurrentEquity(equity: Array<{ ts: string; value: number }> | null | undefined): number | undefined {
  if (!equity || equity.length === 0) return undefined
  return equity[equity.length - 1]?.value
}

export default function MetricsSummary({ metrics, equity, loading }: MetricsSummaryProps) {
  const currentEquity = loading ? null : getCurrentEquity(equity)

  return (
    <section aria-label="Performance metrics" className="rounded border border-slate-200 bg-white">
      <div className="px-3 py-2 border-b border-slate-200 text-slate-700 font-semibold">Performance</div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 p-3">
        {/* Current Equity - first position */}
        <div className="flex flex-col gap-1" title="Current portfolio value from Nautilus">
          <div className="text-xs text-slate-500">Current equity</div>
          <div className="text-base font-medium tabular-nums">{formatCurrency(currentEquity)}</div>
        </div>

        {/* Other metrics */}
        {metricDefs.map((def) => {
          const raw = metrics ? (metrics as any)[def.key] : undefined
          const val = loading ? null : (typeof raw === 'number' ? raw : undefined)
          return (
            <div key={String(def.key)} className="flex flex-col gap-1" title={def.title}>
              <div className="text-xs text-slate-500">{def.label}</div>
              <div className="text-base font-medium tabular-nums">{def.formatter(val)}</div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

