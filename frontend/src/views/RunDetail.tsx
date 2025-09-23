import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getRunDetail, type RunDetail } from '../services/api'
import RunPlayerContainer from '../containers/RunPlayerContainer'

export default function RunDetailView() {
  const { run_id = '' } = useParams()
  const { data, isLoading, isError, error } = useQuery<RunDetail, Error>({
    queryKey: ['run', run_id],
    queryFn: () => getRunDetail(run_id),
    enabled: !!run_id,
  })

  if (isLoading) return <div style={{ padding: 16 }}>Loading	run	metadata		...	</div>
  if (isError) return <div style={{ padding: 16 }}>Error: {error?.message}</div>
  if (!data) return null

  return (
    <div style={{ padding: 16, display: 'grid', gap: 12 }}>
      <div>
        <h2 style={{ margin: 0 }}>Run {data.run_id}</h2>
        <div style={{ color: '#64748B' }}>Strategy {data.strategy_id} — Status {data.status}</div>
      </div>
      <RunPlayerContainer run_id={run_id} />
    </div>
  )
}

