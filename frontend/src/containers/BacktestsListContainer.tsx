import { useMemo, useState, type FormEvent } from 'react'
import { useBacktestList, useCreateBacktest } from '../hooks/useRunData'
import type { BacktestListQuery } from '../services/api'
import BacktestsTable from '../components/BacktestsTable'
import FiltersBar, { type Filters } from '../components/FiltersBar'
import { useNavigate } from 'react-router-dom'

function CreateBacktestForm({ onCreated, creating, setCreating }: { onCreated: (id: string) => void; creating: boolean; setCreating: (v: boolean) => void }) {
  const createBacktest = useCreateBacktest()

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    try {
      setCreating(true)
      const form = new FormData(e.currentTarget)
      const strategy_id = String(form.get('strategy_id') || 'sma_crossover')
      const symbol = String(form.get('symbol') || 'AAPL')
      const run_from = String(form.get('run_from') || '')
      const run_to = String(form.get('run_to') || '')
      const request: any = { strategy_id, symbol }
      if (run_from) request.from = run_from
      if (run_to) request.to = run_to

      const resp = await createBacktest.mutateAsync({
        request,
        idempotencyKey: `ui-${Date.now()}`,
      })
      const id = (resp as any)?.backtest_id || (resp as any)?.run_id
      if (!id) {
        throw new Error('Failed to create backtest: no id returned')
      }
      onCreated(id)
    } finally {
      setCreating(false)
    }
  }

  return (
    <form className="mt-3 flex flex-wrap items-end gap-2" onSubmit={onSubmit}>
      <label className="flex flex-col">
        <span className="text-xs text-slate-500">Strategy</span>
        <select name="strategy_id" defaultValue="sma_crossover" className="input">
          <option value="sma_crossover">sma_crossover</option>
        </select>
      </label>
      <label className="flex flex-col">
        <span className="text-xs text-slate-500">From Date</span>
        <input name="run_from" type="date" defaultValue="2024-10-01" className="input" />
      </label>
      <label className="flex flex-col">
        <span className="text-xs text-slate-500">To Date</span>
        <input name="run_to" type="date" defaultValue="2024-10-31" className="input" />
      </label>
      <label className="flex flex-col">
        <span className="text-xs text-slate-500">Symbol</span>
        <input name="symbol" defaultValue="AAPL" className="input" />
      </label>
      <button type="submit" disabled={creating} className="btn">
        {creating ? 'Starting…' : 'Start Backtest'}
      </button>
    </form>
  )
}

export function BacktestsListContainer() {
  const navigate = useNavigate()
  const [filters, setFilters] = useState<Filters>({})
  const [limit] = useState(20)
  const [offset, setOffset] = useState(0)
  const [creating, setCreating] = useState(false)

  const query: BacktestListQuery = useMemo(
    () => ({ ...filters, limit, offset, order: '-created_at' }),
    [filters, limit, offset],
  )

  const { data, isLoading, isError, error, refetch } = useBacktestList(query)
  const createBacktest = useCreateBacktest()

  async function handleCreateSample() {
    try {
      setCreating(true)
      const resp = await createBacktest.mutateAsync({
        request: {
          strategy_id: 'sma_crossover',
          params: { fast: 20, slow: 50 },
          symbol: 'AAPL',
          year: 2023,
          speed: 60,
          seed: 42,
        },
        idempotencyKey: `sample-${Date.now()}`
      })
      navigate(`/backtests/${resp.backtest_id || resp.run_id}`)
    } catch (e) {
      alert((e as Error).message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="p-4">
      <h1>Backtests</h1>
      <FiltersBar initial={filters} onApply={(f) => { setFilters(f); setOffset(0) }} />
      <CreateBacktestForm onCreated={(id) => navigate(`/backtests/${id}`)} creating={creating} setCreating={setCreating} />

      {isLoading && <div>Loading…</div>}
      {isError && (
        <div>
          Error: {error?.message} <button onClick={() => refetch()}>Retry</button>
        </div>
      )}
      {data && data.items.length === 0 && (
        <div className="mt-3 space-y-2">
          <div>No backtests yet.</div>
          <button onClick={handleCreateSample} disabled={creating}>
            {creating ? 'Creating…' : 'Create Sample Backtest'}
          </button>
        </div>
      )}
      {data && data.items.length > 0 && (
        <>
          <BacktestsTable items={data.items} onView={(id) => navigate(`/backtests/${id}`)} />
          <div className="mt-3 flex items-center gap-2">
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
              Prev
            </button>
            <span>
              Showing {data.items.length} of {data.total} (offset {data.offset})
            </span>
            <button
              disabled={data.offset + data.items.length >= data.total}
              onClick={() => setOffset(offset + limit)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default BacktestsListContainer

