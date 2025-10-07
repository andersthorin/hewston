import { useMemo, useRef, useCallback, useEffect } from 'react'
import { usePlaybackSelector, usePlaybackStore, selectors } from '../../store/playbackClock'

export type TimelineScrubberProps = {
  stepSeconds?: number // keyboard step size
  timeZone?: string // display timezone (e.g., America/New_York)
}

export default function TimelineScrubber({
  stepSeconds = 60,
  timeZone = 'America/New_York',
}: TimelineScrubberProps) {
  const store = usePlaybackStore()
  const range = usePlaybackSelector(selectors.range)
  const current = usePlaybackSelector(selectors.currentTs)
  const markers = usePlaybackSelector(selectors.filteredMarkers)
  const totalFrames = usePlaybackSelector(selectors.totalFrames)
  const currentFrameIndex = usePlaybackSelector(selectors.currentFrameIndex)
  const barRef = useRef<HTMLDivElement | null>(null)

  const formatIso = useCallback(
    (iso: string | null) => {
      if (!iso) return '…'
      try {
        return new Intl.DateTimeFormat(undefined, {
          timeZone,
          month: 'short',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        }).format(new Date(iso))
      } catch {
        return iso
      }
    },
    [timeZone],
  )

  const pct = useMemo(() => {
    if (typeof totalFrames === 'number' && totalFrames > 0) {
      const p = (currentFrameIndex / totalFrames) * 100
      return Math.min(100, Math.max(0, p))
    }
    if (!current || !range.start || !range.end) return 0
    const cur = new Date(current).getTime()
    const start = new Date(range.start).getTime()
    const end = new Date(range.end).getTime()
    if (!(isFinite(cur) && isFinite(start) && isFinite(end) && end > start)) return 0
    return Math.min(100, Math.max(0, ((cur - start) / (end - start)) * 100))
  }, [current, range.start, range.end, totalFrames, currentFrameIndex])

  const seekToPct = useCallback(
    (p: number) => {
      if (!range.start || !range.end) return
      const start = new Date(range.start).getTime()
      const end = new Date(range.end).getTime()
      const target = new Date(Math.round(start + (end - start) * p)).toISOString()
      store.seek(target)
    },
    [range.start, range.end, store],
  )

  const onClick = (e: React.MouseEvent) => {
    const el = barRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const rel = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
    seekToPct(rel)
  }

  // Keyboard accessibility
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!current) return
    const cur = new Date(current).getTime()
    const delta = (e.key === 'ArrowLeft' ? -1 : e.key === 'ArrowRight' ? 1 : 0) * stepSeconds * 1000
    if (delta === 0) return
    e.preventDefault()
    const target = new Date(cur + delta).toISOString()
    store.seek(target)
  }

  // Ensure focus outline visible when keyboard used
  useEffect(() => {
    const el = barRef.current
    if (el) el.style.outline = 'none'
  }, [])

  return (
    <div className="w-full">
      <div
        role="slider"
        aria-label="Timeline scrubber"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(pct)}
        tabIndex={0}
        ref={barRef}
        onClick={onClick}
        onKeyDown={onKeyDown}
        className="relative h-3 rounded bg-slate-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <div
          className="absolute top-0 left-0 h-3 rounded bg-indigo-400"
          style={{ width: `${pct}%` }}
        />
        {markers.slice(0, 200).map((ts) => (
          <Marker key={ts} ts={ts} range={range} />
        ))}
      </div>
      <div className="mt-1 text-xs text-slate-500">
        {formatIso(range.start)} → {formatIso(current)} → {formatIso(range.end)}
      </div>
    </div>
  )
}

function Marker({
  ts,
  range,
}: {
  ts: string
  range: { start: string | null; end: string | null }
}) {
  const left = useMemo(() => {
    if (!range.start || !range.end) return 0
    const t = new Date(ts).getTime()
    const s = new Date(range.start).getTime()
    const e = new Date(range.end).getTime()
    if (!(isFinite(t) && isFinite(s) && isFinite(e) && e > s)) return 0
    return Math.min(100, Math.max(0, ((t - s) / (e - s)) * 100))
  }, [ts, range.start, range.end])
  return (
    <div
      className="absolute top-0 h-3 w-0.5 bg-slate-600 opacity-60"
      style={{ left: `${left}%` }}
    />
  )
}
