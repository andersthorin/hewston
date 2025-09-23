import { useState } from 'react'

export type Filters = { symbol?: string; strategy_id?: string }
export type FiltersBarProps = { initial?: Filters; onApply: (f: Filters) => void }

export function FiltersBar({ initial, onApply }: FiltersBarProps) {
  const [symbol, setSymbol] = useState(initial?.symbol ?? '')
  const [strategyId, setStrategyId] = useState(initial?.strategy_id ?? '')
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
      <input
        placeholder="Symbol"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
      />
      <input
        placeholder="Strategy"
        value={strategyId}
        onChange={(e) => setStrategyId(e.target.value)}
      />
      <button onClick={() => onApply({ symbol, strategy_id: strategyId })}>Apply</button>
    </div>
  )
}

export default FiltersBar

