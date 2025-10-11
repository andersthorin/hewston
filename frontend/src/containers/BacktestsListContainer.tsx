import { useMemo, useState, type FormEvent } from 'react'
import { useBacktestList, useCreateBacktest } from '../hooks/useRunData'
import type { BacktestListQuery, CreateBacktestRequest } from '../services/api'
import BacktestsTable from '../components/BacktestsTable'
import FiltersBar, { type Filters } from '../components/FiltersBar'
import { useNavigate } from 'react-router-dom'
import { apiPost } from '../utils/api'

function CreateBacktestForm({
  onCreated,
  creating,
  setCreating,
}: {
  onCreated: (id: string) => void
  creating: boolean
  setCreating: (v: boolean) => void
}) {
  const createBacktest = useCreateBacktest()
  const [agentic, setAgentic] = useState(false)
  const [plan, setPlan] = useState<any | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    try {
      setCreating(true)
      const form = new FormData(e.currentTarget)
      const run_from = String(form.get('run_from') || '')
      const run_to = String(form.get('run_to') || '')

      if (agentic) {
        // Agentic flow: Start directly using proposed plan (or propose on-the-fly)
        const usePlan = plan ?? (await apiPost('/api/v1/agentic/propose_plan', { from_date: run_from, to_date: run_to }))
        const resp = await apiPost<{ run_ids: string[] }>('/api/v1/agentic/start', { plan: usePlan })
        if (!resp?.run_ids?.length) throw new Error('No runs started')
        // Stay on list; refresh happens via query invalidation outside
        return
      }

      // Manual flow
      const strategy_id = String(form.get('strategy_id') || 'sma_crossover')
      const symbol = String(form.get('symbol') || 'AAPL')
      const request: CreateBacktestRequest = { strategy_id, symbol }
      if (run_from) request.run_from = run_from
      if (run_to) request.run_to = run_to

      const resp = await createBacktest.mutateAsync({
        request,
        idempotencyKey: `ui-${Date.now()}`,
      })
      const r = resp as { backtest_id?: string; run_id?: string }
      const id = r.backtest_id ?? r.run_id
      if (!id) {
        throw new Error('Failed to create backtest: no id returned')
      }
      onCreated(id)
    } catch (e: any) {
      setError(e?.message || 'Failed to submit')
    } finally {
      setCreating(false)
    }
  }

  async function onPreview(e: FormEvent<HTMLButtonElement>) {
    e.preventDefault()
    setError(null)
    try {
      setCreating(true)
      const form = (e.currentTarget as HTMLButtonElement).form
      if (!form) return
      const fd = new FormData(form)
      const run_from = String(fd.get('run_from') || '')
      const run_to = String(fd.get('run_to') || '')
      const p = await apiPost('/api/v1/agentic/propose_plan', { from_date: run_from, to_date: run_to })
      setPlan(p)
    } catch (e: any) {
      setError(e?.message || 'Failed to propose plan')
    } finally {
      setCreating(false)
    }
  }

  return (
    <form className="mt-3 flex flex-wrap items-end gap-2" onSubmit={onSubmit}>
      <label className="flex items-center gap-2">
        <input type="checkbox" checked={agentic} onChange={(e) => setAgentic(e.target.checked)} />
        <span>Agentic Mode</span>
      </label>
      <label className="flex flex-col">
        <span className="text-xs text-slate-500">From Date</span>
        <input name="run_from" type="date" defaultValue="2024-10-01" className="input" />
      </label>
      <label className="flex flex-col">
        <span className="text-xs text-slate-500">To Date</span>
        <input name="run_to" type="date" defaultValue="2024-10-31" className="input" />
      </label>

      {!agentic && (
        <>
          <label className="flex flex-col">
            <span className="text-xs text-slate-500">Strategy</span>
            <select name="strategy_id" defaultValue="sma_crossover" className="input">
              <option value="sma_crossover">sma_crossover</option>
            </select>
          </label>
          <label className="flex flex-col">
            <span className="text-xs text-slate-500">Symbol</span>
            <input name="symbol" defaultValue="AAPL" className="input" />
          </label>
        </>
      )}

      {agentic ? (
        <div className="flex items-end gap-2">
          <button onClick={onPreview} disabled={creating} className="btn" type="button">
            {creating ? 'Proposing…' : 'Preview Plan'}
          </button>
          <button type="submit" disabled={creating} className="btn-primary">
            {creating ? 'Starting…' : 'Start Agentic Run'}
          </button>
        </div>
      ) : (
        <button type="submit" disabled={creating} className="btn">
          {creating ? 'Starting…' : 'Start Backtest'}
        </button>
      )}

      {agentic && plan && (
        <div className="basis-full mt-2 p-2 rounded bg-slate-50 text-xs">
          <div className="font-semibold mb-1">Plan Preview</div>
          <div>Symbols: {(plan.universe?.included || []).map((s: any) => s.symbol).join(', ') || 'None'}</div>
          <div>Strategies: {(plan.strategies || []).map((s: any) => s.strategy_id).join(', ') || 'None'}</div>
          <div className="text-slate-500">Coverage threshold: {String(plan.guardrails?.coverage_threshold ?? 0.9)}</div>
        </div>
      )}

      {error && (
        <div className="basis-full text-red-600 text-sm mt-1" role="alert">
          {error}
        </div>
      )}
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
      await createBacktest.mutateAsync({
        request: {
          strategy_id: 'sma_crossover',
          params: { fast: 20, slow: 50 },
          symbol: 'AAPL',
          speed: 60,
          seed: 42,
        },
        idempotencyKey: `sample-${Date.now()}`,
      })
      // Stay on the list; the query invalidation will refresh items and show status badges.
      // (No auto-navigation to detail page.)
    } catch (e) {
      alert((e as Error).message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="p-4">
      <h1>Backtests</h1>
      <FiltersBar
        initial={filters}
        onApply={(f) => {
          setFilters(f)
          setOffset(0)
        }}
      />
      <CreateBacktestForm
        onCreated={() => {
          /* stay on list; react-query invalidation will refresh */
        }}
        creating={creating}
        setCreating={setCreating}
      />

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
