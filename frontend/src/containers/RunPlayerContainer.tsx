import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchHour, type HourResponse } from '../services/bars'

import { useRunPlayback } from '../services/ws'
import PlaybackControls from '../components/PlaybackControls'
import ChartOHLC, { type CandlestickChartAPI } from '../components/ChartOHLC'
import type { CandlestickData } from 'lightweight-charts'


export type RunPlayerContainerProps = { run_id: string; dataset_id?: string }

export function RunPlayerContainer({ run_id, dataset_id }: RunPlayerContainerProps) {
  // Derive symbol from dataset_id if available (format: SYMBOL-YEAR-1m)
  const symbol = (dataset_id?.split('-')[0] || '').toUpperCase() || undefined

  // Fetch hourly bars for the dataset year (RTH aligned)
  const year = dataset_id?.split('-')[1]
  const from = year ? `${year}-01-01` : undefined
  const to = year ? `${year}-12-31` : undefined
  const { data: hourResp, isError: isHourErr } = useQuery<HourResponse, Error>({
    queryKey: ['hour', symbol, year],
    queryFn: () => fetchHour(symbol!, from!, to!, true),
    enabled: !!symbol && !!year,
    staleTime: 5 * 60 * 1000,
  })

  const { state, onPlay, onPause, subscribe } = useRunPlayback(run_id)

  // Track the actual run window from the streaming frames (first/last)
  const [runFrom, setRunFrom] = useState<string | null>(null)
  const [runTo, setRunTo] = useState<string | null>(null)

  // Subscribe to frames to infer run window
  useEffect(() => {
    const unsub = subscribe((f: any) => {
      try {
        const ts: string | undefined = (f && (f.ts || (f.equity && f.equity.ts))) as any
        if (!ts) return
        const day = ts.slice(0, 10)
        setRunFrom(prev => (prev && prev <= day ? prev : day))
        setRunTo(prev => (prev && prev >= day ? prev : day))
      } catch {}
    })
    return unsub
  }, [subscribe])

  // Imperative chart refs
  const ohlcRef = useRef<CandlestickChartAPI>(null)

  // Candlestick playback cursors and ticker (daily/api-sim via hourly snapshots)
  const hourTickerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const dayKeysRef = useRef<string[] | null>(null)
  const dayIdxRef = useRef<number>(0)
  const hourIdxRef = useRef<number>(0)


  // Group hourly bars by day and precompute cumulative daily snapshots per hour
  const dailySnapshotsRef = useRef<Map<string, Array<{ o: number, h: number, l: number, c: number }>> | null>(null)


  useEffect(() => {
    // On run change, clear the candlestick series
    ohlcRef.current?.reset([])
  }, [run_id])
  // Run change, new hourly data, or new inferred window: reset playback indices and clear ticker
  useEffect(() => {
    dayKeysRef.current = null
    dayIdxRef.current = 0
    hourIdxRef.current = 0
    if (hourTickerRef.current) { clearInterval(hourTickerRef.current); hourTickerRef.current = null }
  }, [run_id, hourResp, runFrom, runTo])

  // Prepare daily snapshots (cumulative per hour) grouped by day
  useEffect(() => {
    if (!hourResp?.bars) { dailySnapshotsRef.current = null; dayKeysRef.current = null; return }

    const byDay = new Map<string, Array<{ o: number, h: number, l: number, c: number }>>()
    // bars are sorted by time; build cumulative OHLC per calendar day
    let curDay: string | null = null
    let o: number | null = null, h = -Infinity, l = Infinity, c: number | null = null
    for (const b of hourResp.bars) {
      const ts = new Date(b.t)
      const day = ts.toISOString().slice(0, 10)
      if (curDay !== day) {
        // flush previous day if any
        if (curDay && o != null && c != null && isFinite(h) && isFinite(l)) {
          // ensure we pushed the last snapshot for the previous day
        }
        curDay = day; o = null; h = -Infinity; l = Infinity; c = null
      }
      o = o ?? b.o; h = Math.max(h, b.h); l = Math.min(l, b.l); c = b.c
      const arr = byDay.get(day) || []
      arr.push({ o: o!, h, l, c: c! })
      byDay.set(day, arr)
    }
    // Restrict to the inferred run window if known
    let keys = Array.from(byDay.keys()).sort()
    if (runFrom && runTo) {
      keys = keys.filter((d) => d >= runFrom && d <= runTo)
    }
    const filtered = new Map<string, Array<{ o: number, h: number, l: number, c: number }>>()
    for (const k of keys) {
      const v = byDay.get(k)
      if (v) filtered.set(k, v)
    }
    // assign refs
    dailySnapshotsRef.current = filtered
    dayKeysRef.current = keys
  }, [hourResp, runFrom, runTo])

  // Hourly ticker driving realtime-style daily playback (mutate same daily bar per hour)
  // Runs a 100ms timer and advances logical ticks based on elapsed time; fixed 1× (1000 ms per tick).
  useEffect(() => {
    // Always recreate ticker when play state or window changes
    if (hourTickerRef.current) { clearInterval(hourTickerRef.current); hourTickerRef.current = null }
    if (!state.playing) return
    if (!dailySnapshotsRef.current || !dayKeysRef.current || dayKeysRef.current.length === 0) return

    const period = 100 // ms per logical tick at fixed 10×
    let last = Date.now()
    let acc = 0

    hourTickerRef.current = setInterval(() => {
      const now = Date.now()
      acc += now - last
      last = now

      while (acc >= period) {
        acc -= period
        const keys = dayKeysRef.current!
        if (dayIdxRef.current >= keys.length) {
          clearInterval(hourTickerRef.current!); hourTickerRef.current = null; return
        }
        const day = keys[dayIdxRef.current]
        const snaps = dailySnapshotsRef.current!.get(day) || []
        if (snaps.length === 0) { dayIdxRef.current++; hourIdxRef.current = 0; continue }
        const y = parseInt(day.slice(0,4)), m = parseInt(day.slice(5,7)), d = parseInt(day.slice(8,10))
        const i = hourIdxRef.current
        const s = snaps[i]
        if (!s) { dayIdxRef.current++; hourIdxRef.current = 0; continue }

        const dp: CandlestickData = { time: { year: y, month: m, day: d } as any, open: s.o, high: s.h, low: s.l, close: s.c }
        ohlcRef.current?.update(dp)

        hourIdxRef.current = i + 1
        if (hourIdxRef.current >= snaps.length) { dayIdxRef.current++; hourIdxRef.current = 0 }
      }
    }, 100) // 100ms base cadence; logical ticks based on 'period'

    return () => { if (hourTickerRef.current) { clearInterval(hourTickerRef.current); hourTickerRef.current = null } }
  }, [state.playing, runFrom, runTo])


  const formatTime = (t: any, locale?: string) => {
    try {
      let d: Date
      if (typeof t === 'number') d = new Date(t * 1000)
      else if (typeof t === 'string') d = new Date(t)
      else if (t && typeof t === 'object' && 'year' in t && 'month' in t && 'day' in t) {
        d = new Date(Date.UTC((t as any).year, (t as any).month - 1, (t as any).day))
      } else return String(t)
      return new Intl.DateTimeFormat(locale || undefined, { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(d)
    } catch {
      return String(t)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <PlaybackControls playing={state.playing} onPlay={onPlay} onPause={onPause} />
        <div className="flex items-center gap-2">
          <div className="text-slate-500">Transport: {state.status} · Candles: daily/api-sim</div>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4">
        <ChartOHLC ref={ohlcRef} formatTime={formatTime} />
        {isHourErr ? <div className="text-sm text-amber-600">No hourly data for {symbol} in this range.</div> : null}
      </div>
    </div>
  )
}

export default RunPlayerContainer
