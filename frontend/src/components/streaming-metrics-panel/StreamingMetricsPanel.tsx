import { useEffect, useRef } from 'react'
import { MetricsSummary } from '../metrics-summary'
import { usePlaybackSelector, selectors } from '../../store/playbackClock'

type FinalMetrics = {
  total_return?: number | null
  sharpe_ratio?: number | null
  max_drawdown?: number | null
  win_rate?: number | null
  realized_pnl?: number | null
  return?: number | null
  ending_balance?: number | null
  ending_equity?: number | null
  unrealized_pnl?: number | null
}

export default function StreamingMetricsPanel({ finalMetrics }: { finalMetrics?: FinalMetrics }) {
  // Force a render on every frame by also subscribing to current timestamp
  const ts = usePlaybackSelector(selectors.currentTs)
  const frame = usePlaybackSelector(selectors.frame)

  const m = frame?.metrics ?? undefined
  const mappedStream = {
    total_return: m?.total_return ?? undefined,
    return: m?.return ?? undefined,
    max_drawdown: m?.drawdown ?? undefined,
    sharpe_ratio: m?.sharpe ?? undefined,
    win_rate: m?.win_rate ?? undefined,
    realized_pnl: m?.realized_pnl ?? undefined,
  }
  // While playing, prefer streaming values; when at end, prefer final Nautilus metrics for exactness
  let mapped = mappedStream

  const eq = frame?.equity
  const currentIndex = usePlaybackSelector(selectors.currentFrameIndex)
  const totalFrames = usePlaybackSelector(selectors.totalFrames)
  const atEnd = typeof totalFrames === 'number' && totalFrames > 0 && currentIndex >= totalFrames

  // Playback behavior:
  // - Use streaming equity while playing/scrubbing
  // - If we're at the final frame and finalMetrics exist, snap to the exact Nautilus Balances ending (cash)
  const endValue =
    finalMetrics && typeof finalMetrics.ending_balance === 'number'
      ? (finalMetrics.ending_balance as number)
      : finalMetrics && typeof finalMetrics.ending_equity === 'number'
        ? (finalMetrics.ending_equity as number)
        : finalMetrics && typeof finalMetrics.total_return === 'number'
          ? 10000 * (1 + (finalMetrics.total_return as number))
          : undefined
  const equityList =
    atEnd && typeof endValue === 'number'
      ? [{ ts: (ts as string) || new Date().toISOString(), value: endValue }]
      : eq && typeof eq.value === 'number'
        ? [{ ts: eq.ts, value: eq.value }]
        : typeof endValue === 'number'
          ? [{ ts: (ts as string) || new Date().toISOString(), value: endValue }]
          : null

  // On the final frame, override all key metrics with canonical Nautilus values when available
  if (atEnd && finalMetrics) {
    const overrides: Record<string, number | null | undefined> = {}
    if (typeof finalMetrics.total_return === 'number')
      overrides.total_return = finalMetrics.total_return
    if (typeof finalMetrics.max_drawdown === 'number')
      overrides.max_drawdown = finalMetrics.max_drawdown
    if (typeof finalMetrics.sharpe_ratio === 'number')
      overrides.sharpe_ratio = finalMetrics.sharpe_ratio
    if (typeof finalMetrics.win_rate === 'number') overrides.win_rate = finalMetrics.win_rate
    if (typeof finalMetrics.realized_pnl === 'number')
      overrides.realized_pnl = finalMetrics.realized_pnl
    mapped = { ...mapped, ...overrides }
  }

  // Debug: log only when values change; cap to first 20 lines
  const lastRef = useRef<{
    ts?: string | null
    tr?: number | null
    dd?: number | null
    sh?: number | null
  }>({})
  const dbgCountRef = useRef(0)
  useEffect(() => {
    if (!import.meta.env.DEV) return
    if (dbgCountRef.current >= 20) return
    const tr = mapped.total_return ?? null
    const dd = mapped.max_drawdown ?? null
    const sh = mapped.sharpe_ratio ?? null
    const changed =
      ts !== lastRef.current.ts ||
      tr !== lastRef.current.tr ||
      dd !== lastRef.current.dd ||
      sh !== lastRef.current.sh
    if (changed) {
      console.debug('[metrics-frame]', { ts, tr, dd, sh, hasEquity: !!eq, eq: eq?.value })
      lastRef.current = { ts, tr, dd, sh }
      dbgCountRef.current += 1
    }
  }, [ts, mapped.total_return, mapped.max_drawdown, mapped.sharpe_ratio, eq, eq?.value])

  return <MetricsSummary metrics={mapped} equity={equityList} />
}
