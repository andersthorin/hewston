import { useParams } from 'react-router-dom'
import { useBacktestDetail } from '../hooks/useRunData'
import RunPlayerContainer from '../containers/RunPlayerContainer'
import ErrorBoundary from '../components/ErrorBoundary'
import MetricsSummary from '../components/MetricsSummary'
import StreamingMetricsPanel from '../components/StreamingMetricsPanel'
import SymbolFocus from '../components/SymbolFocus'

export default function BacktestDetailView() {
  const params = useParams()
  const backtest_id = (params as any).backtest_id || ''
  const { data, isLoading, isError, error } = useBacktestDetail(backtest_id, !!backtest_id)

  const status = data?.status
  const isDone = status === 'DONE' || status === 'COMPLETED'
  const isErrorStatus = status === 'ERROR' || status === 'FAILED'
  const shortError = (data?.error_message || '').slice(0, 120)

  return (
    <div className="p-4 grid gap-3">
      <div>
        <h2 className="m-0">Backtest {data?.backtest_id || backtest_id}</h2>
        <div className="text-slate-500 flex items-center gap-2">
          {isLoading ? (
            'Loading backtest metadata...'
          ) : isError ? (
            <>Error: {error?.message}</>
          ) : data ? (
            <>
              <span>Strategy {data.strategy_id} — Status {data.status}</span>
              {isDone ? (
                <span
                  className="inline-flex items-center rounded bg-emerald-100 text-emerald-700 px-2 py-0.5 text-xs"
                  title="Real engine (no stub fallback)"
                  aria-label="Engine: Nautilus Trader"
                >
                  Engine: Nautilus Trader
                </span>
              ) : null}
            </>
          ) : null}
        </div>
      </div>

      {isErrorStatus ? (
        <div
          role="alert"
          aria-live="assertive"
          className="rounded border border-rose-300 bg-rose-50 text-rose-700 px-3 py-2"
        >
          Backtest failed to start: {shortError || 'Backtest failed. See run manifest for details.'}
        </div>
      ) : null}

      {!isErrorStatus && (
        <>
          <MetricsSummary
            metrics={(data as any)?.metrics ?? undefined}
            equity={(data as any)?.equity ?? undefined}
            loading={isLoading}
          />
          {/* Symbol focus (E11.3) */}
          <SymbolFocus />

          <ErrorBoundary title="Playback viewer crashed">
            <RunPlayerContainer
              backtest_id={backtest_id}
              dataset_id={data?.dataset_id || undefined}
              run_from={data?.run_from ?? undefined}
              run_to={data?.run_to ?? undefined}
            />
          </ErrorBoundary>

          {/* Live streaming metrics (E11.2 stream) */}
          <StreamingMetricsPanel />
        </>
      )}
    </div>
  )
}

