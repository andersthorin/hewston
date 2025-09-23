import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listBacktests, type ListRunsResponse, type ListRunsQuery, createBacktest } from '../services/api'
import RunsTable from '../components/RunsTable'
import FiltersBar, { type Filters } from '../components/FiltersBar'
import { useNavigate } from 'react-router-dom'

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
    <div style={{ padding: 16 }}>
      <h1>Runs</h1>
      <FiltersBar initial={filters} onApply={(f) => { setFilters(f); setOffset(0) }} />
      <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
        <button onClick={handleCreateSample} disabled={creating}>
          {creating ? 'Creating…' : 'Create Sample Run'}
        </button>
      </div>

      {isLoading && <div>Loading…</div>}
      {isError && (
        <div>
          Error: {error?.message} <button onClick={() => refetch()}>Retry</button>
        </div>
      )}
      {data && data.items.length === 0 && (
        <div style={{ marginTop: 12 }}>
          <div>No runs yet.</div>
          <button onClick={handleCreateSample} disabled={creating}>
            {creating ? 'Creating…' : 'Create Sample Run'}
          </button>
        </div>
      )}
      {data && data.items.length > 0 && (
        <>
          <RunsTable items={data.items} onView={(id) => navigate(`/runs/${id}`)} />
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 12 }}>
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

