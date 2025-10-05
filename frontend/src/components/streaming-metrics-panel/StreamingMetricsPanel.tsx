import { useEffect, useRef } from 'react'
import { MetricsSummary } from '../metrics-summary'
import { usePlaybackSelector, selectors } from '../../store/playbackClock'

export default function StreamingMetricsPanel() {
  // Force a render on every frame by also subscribing to current timestamp
  const ts = usePlaybackSelector(selectors.currentTs)
  const frame = usePlaybackSelector(selectors.frame)
  const live = usePlaybackSelector(selectors.metricsLive)

  const m = frame?.metrics
  const mapped = {
    total_return: (m?.total_return_so_far ?? live?.total_return_so_far) ?? undefined,
    max_drawdown: (m?.max_drawdown_so_far ?? live?.max_drawdown_so_far) ?? undefined,
    sharpe_ratio: (m?.sharpe_so_far ?? live?.sharpe_so_far) ?? undefined,
  }
  const eq = frame?.equity
  const equityList = eq ? [{ ts: eq.ts, value: eq.value }] : null

  // Debug: log only when values change; cap to first 20 lines
  const lastRef = useRef<{ ts?: string|null, tr?: number|null, dd?: number|null, sh?: number|null }>({})
  const dbgCountRef = useRef(0)
  useEffect(() => {
    if (!import.meta.env.DEV) return
    if (dbgCountRef.current >= 20) return
    const tr = mapped.total_return ?? null
    const dd = mapped.max_drawdown ?? null
    const sh = mapped.sharpe_ratio ?? null
    const changed = ts !== lastRef.current.ts || tr !== lastRef.current.tr || dd !== lastRef.current.dd || sh !== lastRef.current.sh
    if (changed) {
      console.debug('[metrics-frame]', { ts, tr, dd, sh, hasEquity: !!eq, eq: eq?.value })
      lastRef.current = { ts, tr, dd, sh }
      dbgCountRef.current += 1
    }
  }, [ts, mapped.total_return, mapped.max_drawdown, mapped.sharpe_ratio, eq, eq?.value])

  return <MetricsSummary metrics={mapped} equity={equityList} />
}

