import { useEffect, useRef, useState } from 'react'
import { useRunPlayback } from '../services/ws'
import PlaybackControls from '../components/PlaybackControls'
import ChartOHLC, { type CandlestickChartAPI } from '../components/ChartOHLC'
import EquityChart, { type LineChartAPI } from '../components/EquityChart'
import type { StreamFrameT } from '../schemas/stream'
import type { CandlestickData, LineData } from 'lightweight-charts'

import { nyBusinessDayKey } from '../lib/nyDay'

export type RunPlayerContainerProps = { run_id: string }

export function RunPlayerContainer({ run_id }: RunPlayerContainerProps) {
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
    dailyMapRef.current.forEach((v, k) => out.push({ time: k as any, open: v.open, high: v.high, low: v.low, close: v.close }))
    return out
  }

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

      // Render path: minute or daily
      if (mode === 'minute') {
        if (f.ohlc) {
          const last = lastOhlcTsRef.current
          if (!(last != null && tsSec < last)) {
            const dp: CandlestickData = {
              time: tsSec as any,
              open: f.ohlc.o ?? 0, high: f.ohlc.h ?? 0, low: f.ohlc.l ?? 0, close: f.ohlc.c ?? 0,
            }
            lastOhlcTsRef.current = tsSec
            ohlcRef.current?.update(dp)
          }
        }
      } else {
        if (f.ohlc) {
          const dayKey = nyBusinessDayKey(f.ts)
          const lastKey = lastDailyKeyRef.current
          if (!(lastKey && dayKey < lastKey)) {
            const agg = dailyMapRef.current.get(dayKey)!
            const dp: CandlestickData = { time: dayKey as any, open: agg.open, high: agg.high, low: agg.low, close: agg.close }
            lastDailyKeyRef.current = dayKey
            ohlcRef.current?.update(dp)
          }
        }
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
  // Mode switch: reset OHLC with appropriate history
  useEffect(() => {
    if (mode === 'daily') {
      ohlcRef.current?.reset(dailyArray())
      lastDailyKeyRef.current = null
    } else {
      ohlcRef.current?.reset([])
      lastOhlcTsRef.current = null
    }
  }, [mode])


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
          <div className="text-slate-500">Transport: {state.status} · Frames: {framesCount} · Dropped: {state.dropped}{state.status==='ws' && state.playing && framesCount===0 ? ' · No frames yet…' : ''}</div>
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
