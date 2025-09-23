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
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr>
          <th>run_id</th>
          <th>created_at</th>
          <th>strategy_id</th>
          <th>status</th>
          <th>symbol</th>
          <th>from</th>
          <th>to</th>
          <th>duration_ms</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <tr key={r.run_id}>
            <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, monospace' }}>{r.run_id}</td>
            <td>{r.created_at}</td>
            <td>{r.strategy_id}</td>
            <td>{r.status}</td>
            <td>{r.symbol ?? ''}</td>
            <td>{r.from ?? ''}</td>
            <td>{r.to ?? ''}</td>
            <td>{r.duration_ms ?? ''}</td>
            <td>
              <button onClick={() => onView?.(r.run_id)}>View</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default RunsTable

