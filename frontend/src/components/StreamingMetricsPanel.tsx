import MetricsSummary from './MetricsSummary'
import { usePlaybackSelector, selectors } from '../store/playbackClock'

export default function StreamingMetricsPanel() {
  const frame = usePlaybackSelector(selectors.frame)
  const m = frame?.metrics
  const mapped = m ? {
    total_return: m.total_return_so_far ?? undefined,
    max_drawdown: m.max_drawdown_so_far ?? undefined,
    sharpe_ratio: m.sharpe_so_far ?? undefined,
  } : undefined
  const eq = frame?.equity
  const equityList = eq ? [{ ts: eq.ts, value: eq.value }] : null
  return <MetricsSummary metrics={mapped} equity={equityList} />
}

