import { useMemo, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listBacktests, type ListRunsResponse, type ListRunsQuery, createBacktest } from '../services/api'
import RunsTable from '../components/RunsTable'
import FiltersBar, { type Filters } from '../components/FiltersBar'
import { useNavigate } from 'react-router-dom'

type CreateRunFormProps = { onCreated: (run_id: string) => void; creating: boolean; setCreating: (v: boolean) => void }
function CreateRunForm({ onCreated, creating, setCreating }: CreateRunFormProps) {
  const [symbol, setSymbol] = useState('MSFT')
  const [strategyId, setStrategyId] = useState('sma_crossover')
  const [fromDate, setFromDate] = useState('2024-10-01')
  const [toDate, setToDate] = useState('2024-10-31')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!symbol) return alert('Enter symbol')
    if (!fromDate || !toDate) return alert('Pick start and end dates')
    const y1 = new Date(fromDate).getUTCFullYear()
    const y2 = new Date(toDate).getUTCFullYear()
    if (y1 !== y2) return alert('Date range must be within the same year for now')
    const year = y1
    try {
      setCreating(true)
      const dataset_id = `${symbol.toUpperCase()}-${year}-1m`
      const resp = await createBacktest({
        strategy_id: strategyId,
        params: { fast: 20, slow: 50 },
        dataset_id,
        from: fromDate || undefined,
        to: toDate || undefined,
        speed: 60,
        seed: 42,
      }, `form-${Date.now()}`)
      onCreated(resp.run_id)
    } catch (e) {
      alert((e as Error).message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-2 mb-3">
      <input className="w-24 px-2 py-1 border border-slate-300 rounded" placeholder="Symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)} />

      <label className="text-slate-600">Strategy:</label>
      <select className="px-2 py-1 border border-slate-300 rounded" value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
        <option value="sma_crossover">SMA Crossover</option>
      </select>
      <input className="px-2 py-1 border border-slate-300 rounded" type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
      <input className="px-2 py-1 border border-slate-300 rounded" type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
      <button className="px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50" type="submit" disabled={creating}>{creating ? 'Starting…' : 'Start Run'}</button>
    </form>
  )
}

export function RunsListContainer() {
  const navigate = useNavigate()
  const [filters, setFilters] = useState<Filters>({})
  const [limit] = useState(20)
  const [offset, setOffset] = useState(0)
  const [creating, setCreating] = useState(false)

  const query: ListRunsQuery = useMemo(
    () => ({ ...filters, limit, offset, order: '-created_at' }),
    [filters, limit, offset],
  )

  const { data, isLoading, isError, error, refetch } = useQuery<ListRunsResponse, Error>({
    queryKey: ['backtests', query],
    queryFn: () => listBacktests(query),
  })

  async function handleCreateSample() {
    try {
      setCreating(true)
      const resp = await createBacktest(
        {
          strategy_id: 'sma_crossover',
          params: { fast: 20, slow: 50 },
          symbol: 'AAPL',
          year: 2023,
          speed: 60,
          seed: 42,
        },
        `sample-${Date.now()}`,
      )
      navigate(`/runs/${resp.run_id}`)
    } catch (e) {
      // simple alert for now
      alert((e as Error).message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="p-4">
      <h1>Runs</h1>
      <FiltersBar initial={filters} onApply={(f) => { setFilters(f); setOffset(0) }} />
      <CreateRunForm onCreated={(id) => navigate(`/runs/${id}`)} creating={creating} setCreating={setCreating} />

      {isLoading && <div>Loading…</div>}
      {isError && (
        <div>
          Error: {error?.message} <button onClick={() => refetch()}>Retry</button>
        </div>
      )}
      {data && data.items.length === 0 && (
        <div className="mt-3 space-y-2">
          <div>No runs yet.</div>
          <button onClick={handleCreateSample} disabled={creating}>
            {creating ? 'Creating…' : 'Create Sample Run'}
          </button>
        </div>
      )}
      {data && data.items.length > 0 && (
        <>
          <RunsTable items={data.items} onView={(id) => navigate(`/runs/${id}`)} />
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

export default RunsListContainer

