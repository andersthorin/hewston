import { useState } from 'react'

export type Filters = { symbol?: string; strategy_id?: string }
export type FiltersBarProps = { initial?: Filters; onApply: (f: Filters) => void }

export function FiltersBar({ initial, onApply }: FiltersBarProps) {
  const [symbol, setSymbol] = useState(initial?.symbol ?? '')
  const [strategyId, setStrategyId] = useState(initial?.strategy_id ?? '')
  return (
    <div className="mb-3 flex items-center gap-2">
      <input
        className="px-2 py-1 border border-slate-300 rounded"
        placeholder="Symbol"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
      />
      <input
        className="px-2 py-1 border border-slate-300 rounded"
        placeholder="Strategy"
        value={strategyId}
        onChange={(e) => setStrategyId(e.target.value)}
      />
      <button className="px-3 py-1 rounded bg-slate-800 text-white hover:bg-slate-700" onClick={() => onApply({ symbol, strategy_id: strategyId })}>Filter</button>
    </div>
  )
}

export default FiltersBar

