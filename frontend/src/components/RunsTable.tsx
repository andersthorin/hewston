import { useQuery } from '@tanstack/react-query'
import { getRunDetail, type RunSummary, type RunDetail } from '../services/api'

export type RunsTableProps = {
  items: RunSummary[]
  onView?: (run_id: string) => void
}

export function RunsTable({ items, onView }: RunsTableProps) {
  if (!items.length) {
    return <div>No runs yet. Create a run to get started.</div>
  }
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-slate-200">
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">run_id</th>
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
          <Row key={r.run_id} r={r} onView={onView} />
        ))}
      </tbody>
    </table>
  )
}

function Row({ r, onView }: { r: RunSummary; onView?: (id: string) => void }) {
  const { data } = useQuery<RunDetail, Error>({
    queryKey: ['run-detail-window', r.run_id],
    queryFn: () => getRunDetail(r.run_id),
    staleTime: 5 * 60 * 1000,
  })
  const runFrom = data?.run_from ?? '—'
  const runTo = data?.run_to ?? '—'
  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50">
      <td className="px-2 py-1 font-mono">{r.run_id}</td>
      <td className="px-2 py-1">{r.created_at}</td>
      <td className="px-2 py-1">{r.strategy_id}</td>
      <td className="px-2 py-1">{r.status}</td>
      <td className="px-2 py-1">{r.symbol ?? ''}</td>
      <td className="px-2 py-1">{runFrom}</td>
      <td className="px-2 py-1">{runTo}</td>
      <td className="px-2 py-1">{r.duration_ms ?? ''}</td>
      <td className="px-2 py-1">
        <button className="px-2 py-1 rounded bg-slate-800 text-white hover:bg-slate-700" onClick={() => onView?.(r.run_id)}>View</button>
      </td>
    </tr>
  )
}


export default RunsTable

