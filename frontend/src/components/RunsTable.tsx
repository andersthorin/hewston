import type { RunSummary } from '../services/api'

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
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">dataset_from</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">dataset_to</th>
          <th className="px-2 py-1 text-left text-slate-600 font-semibold">duration_ms</th>
          <th className="px-2 py-1"></th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <tr key={r.run_id} className="border-b border-slate-100 hover:bg-slate-50">
            <td className="px-2 py-1 font-mono">{r.run_id}</td>
            <td className="px-2 py-1">{r.created_at}</td>
            <td className="px-2 py-1">{r.strategy_id}</td>
            <td className="px-2 py-1">{r.status}</td>
            <td className="px-2 py-1">{r.symbol ?? ''}</td>
            <td className="px-2 py-1">{r.from ?? ''}</td>
            <td className="px-2 py-1">{r.to ?? ''}</td>
            <td className="px-2 py-1">{r.duration_ms ?? ''}</td>
            <td className="px-2 py-1">
              <button className="px-2 py-1 rounded bg-slate-800 text-white hover:bg-slate-700" onClick={() => onView?.(r.run_id)}>View</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default RunsTable

