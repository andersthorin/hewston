import { useParams } from 'react-router-dom'
import { useBacktestDetail } from '../hooks/useRunData'
import RunPlayerContainer from '../containers/RunPlayerContainer'

export default function BacktestDetailView() {
  const params = useParams()
  const backtest_id = (params as any).backtest_id || ''
  const { data, isLoading, isError, error } = useBacktestDetail(backtest_id, !!backtest_id)

  return (
    <div className="p-4 grid gap-3">
      <div>
        <h2 className="m-0">Backtest {data?.backtest_id || backtest_id}</h2>
        <div className="text-slate-500">
          {isLoading ? (
            'Loading backtest metadata...'
          ) : isError ? (
            <>Error: {error?.message}</>
          ) : data ? (
            <>Strategy {data.strategy_id} — Status {data.status}</>
          ) : null}
        </div>
      </div>
      <RunPlayerContainer
        backtest_id={backtest_id}
        dataset_id={data?.dataset_id || undefined}
        run_from={data?.run_from ?? undefined}
        run_to={data?.run_to ?? undefined}
      />
    </div>
  )
}

