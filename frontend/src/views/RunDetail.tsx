import { useParams } from 'react-router-dom'
import { useCompleteRunData } from '../hooks/useRunData'
import RunPlayerContainer from '../containers/RunPlayerContainer'

export default function RunDetailView() {
  const { run_id = '' } = useParams()
  // Use BFF-aware hook for complete run data (includes aggregated metrics, equity, etc.)
  const { data, isLoading, isError, error } = useCompleteRunData(run_id, !!run_id)

  return (
    <div className="p-4 grid gap-3">
      <div>
        <h2 className="m-0">Run {data?.run_id || run_id}</h2>
        <div className="text-slate-500">
          {isLoading ? (
            'Loading run metadata...'
          ) : isError ? (
            <>Error: {error?.message}</>
          ) : data ? (
            <>Strategy {data.strategy_id} — Status {data.status}</>
          ) : null}
        </div>
      </div>
      <RunPlayerContainer
        run_id={run_id}
        dataset_id={data?.dataset_id || undefined}
        run_from={data?.run_from ?? undefined}
        run_to={data?.run_to ?? undefined}
      />
    </div>
  )
}

