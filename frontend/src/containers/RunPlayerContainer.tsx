import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchDaily } from '../services/bars'

import { useRunPlayback } from '../services/ws'
import PlaybackControls from '../components/PlaybackControls'
import ChartOHLC, { type CandlestickChartAPI } from '../components/ChartOHLC'
import EquityChart, { type LineChartAPI } from '../components/EquityChart'
import type { StreamFrameT } from '../schemas/stream'
import type { CandlestickData, LineData } from 'lightweight-charts'

import { nyBusinessDayKey } from '../lib/nyDay'

export type RunPlayerContainerProps = { run_id: string; dataset_id?: string }

export function RunPlayerContainer({ run_id, dataset_id }: RunPlayerContainerProps) {
  // Derive symbol from dataset_id if available (format: SYMBOL-YEAR-1m)
  const symbol = (dataset_id?.split('-')[0] || '').toUpperCase() || undefined

  // Fetch daily series once (complete)
  const { data: dailyResp } = useQuery({
    queryKey: ['daily', symbol],
    queryFn: () => fetchDaily(symbol!),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  })

  type DisplayMode = 'minute' | 'daily'
  const [mode, setMode] = useState<DisplayMode>('minute')

  const { state, subscribe, onPlay, onPause, onSpeedChange } = useRunPlayback(run_id)

  // Imperative chart refs and last-time guards
  const ohlcRef = useRef<CandlestickChartAPI>(null)
  const eqRef = useRef<LineChartAPI>(null)
  const lastOhlcTsRef = useRef<number | null>(null)
  const lastEquityTsRef = useRef<number | null>(null)
  const lastDailyKeyRef = useRef<string | null>(null)

  // Metric only (no full frame accumulation)
  const [framesCount, setFramesCount] = useState(0)

  // Daily aggregation state (dayKey -> candle)
  type Daily = { open: number, high: number, low: number, close: number }
  const dailyMapRef = useRef<Map<string, Daily>>(new Map())

  const dailyArray = (): CandlestickData[] => {
    const out: CandlestickData[] = []
    dailyMapRef.current.forEach((v, k) => {
      const ts = Math.floor(new Date(k + 'T00:00:00Z').getTime() / 1000)
      out.push({ time: ts as any, open: v.open, high: v.high, low: v.low, close: v.close })
    })
    return out
  }

  // Minute aggregation (UTC minute -> candle), and playback tickers
  type MinuteAgg = { open: number, high: number, low: number, close: number }
  const minuteAggRef = useRef<Map<number, MinuteAgg>>(new Map())
  const minuteMinRef = useRef<number | null>(null)
  const minuteMaxRef = useRef<number | null>(null)
  const nextMinutePtrRef = useRef<number | null>(null)

  // Tickers and playback cursors
  const dailyTickerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const minuteTickerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const dailyStartedRef = useRef<boolean>(false)
  const dailyIndexRef = useRef<number>(0)


  useEffect(() => {
    // Reset charts and counters on run change
    setFramesCount(0)
    lastOhlcTsRef.current = null
    lastEquityTsRef.current = null
    lastDailyKeyRef.current = null
    dailyMapRef.current = new Map()
    ohlcRef.current?.reset([])
    eqRef.current?.reset([])

    const unsubscribe = subscribe((f: StreamFrameT) => {
      setFramesCount((c) => c + 1)
      const tsSec = Math.floor(new Date(f.ts).getTime() / 1000)

      // Maintain daily aggregation state
      if (f.ohlc) {
        const dayKey = nyBusinessDayKey(f.ts)
        const prev = dailyMapRef.current.get(dayKey)
        if (!prev) {
          dailyMapRef.current.set(dayKey, { open: f.ohlc.o ?? 0, high: f.ohlc.h ?? 0, low: f.ohlc.l ?? 0, close: f.ohlc.c ?? 0 })
        } else {
          prev.high = Math.max(prev.high, f.ohlc.h ?? prev.high)
          prev.low = Math.min(prev.low, f.ohlc.l ?? prev.low)
          prev.close = f.ohlc.c ?? prev.close
        }
      }

      // Render path: minute or daily (candles driven by client-side ticker)
      if (mode === 'minute') {
        // Buffer per-minute aggregation; ticker will append at 1 Hz
        if (f.ohlc) {
          const minuteStart = Math.floor(tsSec / 60) * 60
          const agg = minuteAggRef.current.get(minuteStart)
          if (!agg) {
            minuteAggRef.current.set(minuteStart, {
              open: f.ohlc.o ?? 0,
              high: f.ohlc.h ?? 0,
              low: f.ohlc.l ?? 0,
              close: f.ohlc.c ?? 0,
            })
          } else {
            agg.high = Math.max(agg.high, f.ohlc.h ?? agg.high)
            agg.low = Math.min(agg.low, f.ohlc.l ?? agg.low)
            agg.close = f.ohlc.c ?? agg.close
          }
          // Track seen minute range
          minuteMinRef.current = minuteMinRef.current == null ? minuteStart : Math.min(minuteMinRef.current, minuteStart)
          minuteMaxRef.current = minuteMaxRef.current == null ? minuteStart : Math.max(minuteMaxRef.current, minuteStart)
        }
      } else {
        // Daily mode uses REST preloaded bars; ticker will drive appends
      }

      // Equity stream → line (minute)
      if (f.equity) {
        const last = lastEquityTsRef.current
        if (!(last != null && tsSec < last)) {
          const dp: LineData = { time: tsSec as any, value: f.equity.value }
          lastEquityTsRef.current = tsSec
          eqRef.current?.update(dp)
        }
      }
    })

    return () => unsubscribe()
  }, [subscribe, run_id, mode])
  // Mode/run change: reset internal candle playback cursors and clear tickers
  useEffect(() => {
    // Reset daily playback state (do not render series immediately)
    dailyStartedRef.current = false
    dailyIndexRef.current = 0
    if (dailyTickerRef.current) { clearInterval(dailyTickerRef.current); dailyTickerRef.current = null }

    // Reset minute playback pointer and ticker; keep aggregation buffer
    nextMinutePtrRef.current = null
    if (minuteTickerRef.current) { clearInterval(minuteTickerRef.current); minuteTickerRef.current = null }
  }, [mode, run_id])

  // Daily ticker: on first Play in daily mode, reset to empty and append 1 bar/sec
  useEffect(() => {
    if (mode !== 'daily') return
    if (!dailyResp?.bars) return

    if (state.playing) {
      if (!dailyStartedRef.current) {
        dailyStartedRef.current = true
        dailyIndexRef.current = 0
        ohlcRef.current?.reset([])
      }
      if (!dailyTickerRef.current) {
        dailyTickerRef.current = setInterval(() => {
          const idx = dailyIndexRef.current
          const bars = dailyResp.bars
          if (!bars || idx >= bars.length) {
            if (dailyTickerRef.current) { clearInterval(dailyTickerRef.current); dailyTickerRef.current = null }
            return
          }
          const b = bars[idx]
          const dp: CandlestickData = { time: Math.floor(new Date(b.t).getTime() / 1000) as any, open: b.o, high: b.h, low: b.l, close: b.c }
          ohlcRef.current?.update(dp)
          dailyIndexRef.current = idx + 1
          if (dailyIndexRef.current >= bars.length) {
            if (dailyTickerRef.current) { clearInterval(dailyTickerRef.current); dailyTickerRef.current = null }
          }
        }, 1000)
      }
    } else {
      if (dailyTickerRef.current) { clearInterval(dailyTickerRef.current); dailyTickerRef.current = null }
    }

    return () => {
      if (dailyTickerRef.current) { clearInterval(dailyTickerRef.current); dailyTickerRef.current = null }
    }
  }, [mode, state.playing, dailyResp])

  // Minute ticker: append one completed minute per second if available
  useEffect(() => {
    if (mode !== 'minute') return

    if (state.playing) {
      if (!minuteTickerRef.current) {
        minuteTickerRef.current = setInterval(() => {
          const minSeen = minuteMinRef.current
          const maxSeen = minuteMaxRef.current
          if (minSeen == null || maxSeen == null) return

          let ptr = nextMinutePtrRef.current
          if (ptr == null) ptr = minSeen

          // Only append if we have aggregation for ptr and it is complete (ptr < latest seen minute)
          if (ptr < maxSeen && minuteAggRef.current.has(ptr)) {
            const agg = minuteAggRef.current.get(ptr)!
            const dp: CandlestickData = { time: ptr as any, open: agg.open, high: agg.high, low: agg.low, close: agg.close }
            ohlcRef.current?.update(dp)
            nextMinutePtrRef.current = ptr + 60
          }
          // else: wait for more data
        }, 1000)
      }
    } else {
      if (minuteTickerRef.current) { clearInterval(minuteTickerRef.current); minuteTickerRef.current = null }
    }

    return () => {
      if (minuteTickerRef.current) { clearInterval(minuteTickerRef.current); minuteTickerRef.current = null }
    }
  }, [mode, state.playing])


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
        <PlaybackControls playing={state.playing} speed={state.speed} onPlay={onPlay} onPause={onPause} onSpeedChange={onSpeedChange} />
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded border border-slate-300 overflow-hidden">
            <button className={`px-2 py-1 text-sm ${mode==='minute' ? 'bg-slate-200' : ''}`} onClick={() => setMode('minute')}>Minute</button>
            <button className={`px-2 py-1 text-sm ${mode==='daily' ? 'bg-slate-200' : ''}`} onClick={() => setMode('daily')}>Daily</button>
          </div>
          <div className="text-slate-500">Transport: {state.status} · Frames: {framesCount} · Dropped: {state.dropped}{state.status==='ws' && state.playing && framesCount===0 ? ' · No frames yet…' : ''} · Candles: {mode==='daily' ? 'daily/api-sim' : 'minute/ws'}</div>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4">
        <ChartOHLC ref={ohlcRef} formatTime={formatTime} />
        <EquityChart ref={eqRef} formatTime={formatTime} />
      </div>
    </div>
  )
}

export default RunPlayerContainer
