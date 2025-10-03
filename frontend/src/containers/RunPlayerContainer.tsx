import { useEffect, useRef, useState } from 'react'
import { useHourChartData } from '../hooks/useChartData'

import { useBacktestPlayback } from '../services/ws'
import { PlaybackControls } from '../components/playback-controls'
import ChartOHLC, { type CandlestickChartAPI } from '../components/ChartOHLC'
import { TimelineScrubber } from '../components/timeline-scrubber'
import OverlaysOrders from '../components/OverlaysOrders'
import playbackStore from '../store/playbackClock'
import type { CandlestickData, Time } from 'lightweight-charts'
import type { StreamFrameT } from '../schemas/stream'

export type RunPlayerContainerProps = { backtest_id: string; dataset_id?: string; run_from?: string; run_to?: string }

function RunPlayerContainer({ backtest_id, dataset_id, run_from, run_to }: RunPlayerContainerProps) {
  // Derive symbol from dataset_id if available (format: SYMBOL-*-1m)
  const symbol = (dataset_id?.split('-')[0] || '').toUpperCase() || undefined

  // Use actual run window only; do not infer from dataset_id
  const from = run_from ?? undefined
  const to = run_to ?? undefined
  const { data: hourResp, isError: isHourErr, isLoading: isHourLoading } = useHourChartData(
    symbol,
    from,
    to,
    true, // rth_only
    !!symbol && !!from && !!to
  )
  useEffect(() => {
    if (!isHourLoading && !isHourErr) {
      const count = hourResp?.bars?.length ?? 0
      console.debug('[RunPlayer] hourly API loaded', { count, symbol, from, to })
    } else if (isHourErr) {
      console.debug('[RunPlayer] hourly API error for', { symbol, from, to })
    }
  }, [isHourLoading, isHourErr, hourResp, symbol, from, to])

  const playback = useBacktestPlayback(backtest_id)
  const { state, onPlay, onPause, onSeek, subscribe } = playback

  // Wire WS controls into playback store controls
  useEffect(() => {
    playbackStore.setControls({ play: onPlay, pause: onPause, seek: onSeek })
  }, [onPlay, onPause, onSeek])

  // Reflect playing state into store
  useEffect(() => { playbackStore._setPlaying(state.playing) }, [state.playing])

  const recvCountRef = useRef(0)
  const readySentRef = useRef(false) // Track if ready signal has been sent

  // Track the actual run window; prefer props (from manifest) and fall back to streaming inference
  const [runFrom, setRunFrom] = useState<string | null>(run_from ?? null)
  const [runTo, setRunTo] = useState<string | null>(run_to ?? null)
  useEffect(() => { setRunFrom(run_from ?? null); }, [run_from])
  useEffect(() => { setRunTo(run_to ?? null); }, [run_to])

  // View mode must be declared before effects that reference it
  const [viewMode, setViewMode] = useState<'daily'|'hourly'>('daily')

  // Subscribe to frames to infer run window only if props not provided
  useEffect(() => {
    const unsub = subscribe((frame: StreamFrameT) => {
      try {
        recvCountRef.current += 1
        if (recvCountRef.current <= 50) {
          const t = frame?.equity?.ts || frame?.ts
          console.debug('[RunPlayer] subscribe: frame received', { n: recvCountRef.current, ts: t })
        }
        // Always forward frame to playback store
        playbackStore._setFrame(frame)

        const tsStr: string | undefined = frame?.equity?.ts || frame?.ts
        const ohlc = frame.ohlc as { o?: number; h?: number; l?: number; c?: number } | undefined | null
        const hasOhlc = !!(ohlc && ohlc.o != null && ohlc.h != null && ohlc.l != null && ohlc.c != null)
        const hasSnapshots = !!(dailySnapshotsRef.current && dayKeysRef.current && dayKeysRef.current.length > 0)

        // Infer run window from frames only if not provided via props
        // This ensures the timeline shows the correct range immediately
        if (tsStr && !runFrom && !runTo) {
          const day = tsStr.slice(0, 10)
          setRunFrom(prev => (prev && prev <= day ? prev : day))
          setRunTo(prev => (prev && prev >= day ? prev : day))
        }

        // Drive the chart from streaming frames first; fall back to hourly snapshots if needed
        if (tsStr) {
          const y = parseInt(tsStr.slice(0,4)), m = parseInt(tsStr.slice(5,7)), d = parseInt(tsStr.slice(8,10))
          if (hasOhlc) {
            const timeVal: Time = (viewMode === 'daily')
              ? ({ year: y, month: m, day: d } as Time)
              : (Math.floor(new Date(tsStr).getTime() / 1000) as unknown as Time)
            const dp: CandlestickData = { time: timeVal, open: ohlc!.o!, high: ohlc!.h!, low: ohlc!.l!, close: ohlc!.c! }
            console.debug('[RunPlayer] frame branch=streaming-ohlc', { ts: tsStr, dp, seeded: seededRef.current, viewMode })
            if (!seededRef.current) { ohlcRef.current?.reset([dp]) } else { ohlcRef.current?.update(dp) }
            ohlcRef.current?.scrollToLatest()
            seededRef.current = true
            lastDayRef.current = tsStr.slice(0,10)
          } else if (hasSnapshots) {
            const day = tsStr.slice(0, 10)
            const snaps = dailySnapshotsRef.current!.get(day) || []
            console.debug('[RunPlayer] frame branch=snapshots', { ts: tsStr, day, snaps: snaps.length, seeded: seededRef.current, viewMode })
            if (snaps.length > 0) {
              // Find the latest snapshot at or before current streaming time
              let idx = snaps.length - 1
              const tms = new Date(tsStr).getTime()
              for (let i = snaps.length - 1; i >= 0; i--) {
                const si = snaps[i]
                const sms = new Date(si.t).getTime()
                if (sms <= tms) { idx = i; break }
              }
              const s = snaps[idx]
              if (s) {
                const timeVal: Time = (viewMode === 'daily')
                  ? ({ year: y, month: m, day: d } as Time)
                  : (Math.floor(new Date(s.t).getTime() / 1000) as unknown as Time)
                const dp: CandlestickData = { time: timeVal, open: s.o, high: s.h, low: s.l, close: s.c }
                console.debug('[RunPlayer] apply snapshot dp', { ts: tsStr, dp })
                if (!seededRef.current) { ohlcRef.current?.reset([dp]) } else { ohlcRef.current?.update(dp) }
                if (day !== lastDayRef.current || !seededRef.current) { ohlcRef.current?.scrollToLatest() }
                seededRef.current = true
                lastDayRef.current = day
              }
            }
          } else {
            // Snapshots not ready yet - this shouldn't happen with wait-for-ready approach
            console.debug('[RunPlayer] frame branch=none (snapshots not ready - unexpected)', { ts: tsStr })
          }
        }
      } catch (error) {
        console.warn('Failed to process frame:', error)
      }
    })
    return unsub
  }, [subscribe, run_from, run_to, runFrom, runTo, viewMode])

  // Imperative chart refs
  const ohlcRef = useRef<CandlestickChartAPI>(null)
  const seededRef = useRef<boolean>(false)

  // Candlestick playback cursors and ticker (daily/api-sim via hourly snapshots)
  const hourTickerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const dayKeysRef = useRef<string[] | null>(null)
  const dayIdxRef = useRef<number>(0)
  const hourIdxRef = useRef<number>(0)

  const lastDayRef = useRef<string | null>(null)


  // Group hourly bars by day and precompute cumulative daily snapshots per hour
  const [snapshotsVersion, setSnapshotsVersion] = useState(0)
  // Keep playback store range in sync with inferred/known run window
  useEffect(() => {
    playbackStore._setRange({ start: runFrom, end: runTo })
  }, [runFrom, runTo])


  const dailySnapshotsRef = useRef<Map<string, Array<{ o: number, h: number, l: number, c: number, t: string }>> | null>(null)


  useEffect(() => {
    // On run change, clear the candlestick series
    ohlcRef.current?.reset([])
  }, [backtest_id])
  // Run change, new hourly data, or new inferred window: reset playback indices and clear ticker
  useEffect(() => {
    dayKeysRef.current = null
    dayIdxRef.current = 0
    hourIdxRef.current = 0
    seededRef.current = false
    if (hourTickerRef.current) { clearInterval(hourTickerRef.current); hourTickerRef.current = null }
  }, [backtest_id, hourResp, runFrom, runTo])

  // Prepare daily snapshots (cumulative per hour) grouped by day
  useEffect(() => {
    // Defer seeding snapshots until we know the run window to avoid pre-window blips
    if (!hourResp?.bars) { dailySnapshotsRef.current = null; dayKeysRef.current = null; return }
    if (!runFrom || !runTo) { dailySnapshotsRef.current = null; dayKeysRef.current = null; return }

    const byDay = new Map<string, Array<{ o: number, h: number, l: number, c: number, t: string }>>()
    // bars are sorted by time; build cumulative OHLC per calendar day
    let curDay: string | null = null
    let o: number | null = null, h = -Infinity, l = Infinity, c: number | null = null
    const bars = hourResp.bars
    for (const b of bars) {
      const tsDate = new Date(b.t)
      const day = tsDate.toISOString().slice(0, 10)
      if (curDay !== day) {
        curDay = day; o = null; h = -Infinity; l = Infinity; c = null
      }
      o = o ?? b.o; h = Math.max(h, b.h); l = Math.min(l, b.l); c = b.c
      const arr = byDay.get(day) || []
      arr.push({ o: o!, h, l, c: c!, t: new Date(b.t).toISOString() })
      byDay.set(day, arr)
    }
    // Restrict to the inferred run window if known
    let keys = Array.from(byDay.keys()).sort()
    if (runFrom && runTo) {
      keys = keys.filter((d) => d >= runFrom && d <= runTo)
    }

    const filtered = new Map<string, Array<{ o: number, h: number, l: number, c: number, t: string }>>()
    for (const k of keys) {
      const v = byDay.get(k)
      if (v) filtered.set(k, v)
    }
    // assign refs
    dailySnapshotsRef.current = filtered
    dayKeysRef.current = keys

    console.debug('[RunPlayer] snapshots built', { days: keys.length, first: keys[0], last: keys[keys.length-1] })
    setSnapshotsVersion((v) => v + 1)
  }, [hourResp, runFrom, runTo])

  // When snapshots become available, send ready signal to backend to start streaming
  useEffect(() => {
    const hasSnapshots = !!(dailySnapshotsRef.current && dayKeysRef.current && dayKeysRef.current.length > 0)
    if (!hasSnapshots) return
    if (readySentRef.current) return // Only send once

    console.debug('[RunPlayer] snapshots ready, sending ready signal to backend')
    readySentRef.current = true

    // Send ready signal to backend via playback service
    if (playback) {
      try {
        playback.sendReady()
        console.debug('[RunPlayer] ready signal sent')
      } catch (err) {
        console.warn('[RunPlayer] failed to send ready signal', err)
      }
    }
  }, [snapshotsVersion, playback])

  // Chart is now driven by streaming frames (see subscribe effect above) to keep it in sync with the scrubber.
  useEffect(() => {
    // When switching view mode, reset series so subsequent frame-driven updates render with correct time type
    ohlcRef.current?.reset([])
  }, [viewMode])


  const formatTime = (t: Time, locale?: string) => {
    try {
      let d: Date
      if (typeof t === 'number') d = new Date(t * 1000)
      else if (typeof t === 'string') d = new Date(t)
      else if (t && typeof t === 'object' && 'year' in t && 'month' in t && 'day' in t) {
        const timeObj = t as { year: number; month: number; day: number }
        d = new Date(Date.UTC(timeObj.year, timeObj.month - 1, timeObj.day))
      } else return String(t)
      return new Intl.DateTimeFormat(locale || undefined, { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(d)
    } catch (error) {
      console.warn('Failed to format time:', error)
      return String(t)
    }

  }


  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <PlaybackControls playing={state.playing} onPlay={onPlay} onPause={onPause} />
        <div className="flex items-center gap-2">
          <div className="text-slate-500">Transport: {state.status}</div>
          <div className="inline-flex rounded border border-slate-300 overflow-hidden text-xs">
            <button className={`px-2 py-1 ${viewMode==='daily'?'bg-slate-200':''}`} onClick={() => setViewMode('daily')}>Daily</button>
            <button className={`px-2 py-1 ${viewMode==='hourly'?'bg-slate-200':''}`} onClick={() => setViewMode('hourly')}>Hourly</button>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4">
        <ChartOHLC ref={ohlcRef} formatTime={formatTime} />
        <OverlaysOrders chartRef={ohlcRef} />
        <TimelineScrubber />
        {!runFrom || !runTo ? <div className="text-sm text-slate-500">Waiting for frames…</div> : null}
        {isHourLoading ? <div className="text-sm text-slate-500">Loading hourly data…</div> : null}
        {isHourErr ? <div className="text-sm text-amber-600">No hourly data for {symbol} in this range.</div> : null}
      </div>
    </div>
  )
}



export default RunPlayerContainer
