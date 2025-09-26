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

  if (isLoading) return <div className="p-4">Loading run metadata...</div>
  if (isError) return <div className="p-4">Error: {error?.message}</div>
  if (!data) return null

  return (
    <div className="p-4 grid gap-3">
      <div>
        <h2 className="m-0">Run {data.run_id}</h2>
        <div className="text-slate-500">Strategy {data.strategy_id} — Status {data.status}</div>
      </div>
      <RunPlayerContainer run_id={run_id} dataset_id={data.dataset_id || undefined} run_from={data.run_from ?? undefined} run_to={data.run_to ?? undefined} />
    </div>
  )
}

