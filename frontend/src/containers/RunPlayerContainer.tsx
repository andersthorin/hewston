import { useEffect, useMemo, useState } from 'react'
import type { StreamFrame } from '../services/api'
import { useRunPlayback } from '../services/ws'
import PlaybackControls from '../components/PlaybackControls'
import ChartOHLC from '../components/ChartOHLC'
import EquityChart from '../components/EquityChart'
import type { CandlestickData, LineData } from 'lightweight-charts'

export type RunPlayerContainerProps = { run_id: string }

export function RunPlayerContainer({ run_id }: RunPlayerContainerProps) {
  const [frames, setFrames] = useState<StreamFrame[]>([])
  const { state, subscribe, onPlay, onPause, onSpeedChange } = useRunPlayback(run_id)

  useEffect(() => {
    setFrames([])
    const unsubscribe = subscribe((f) => setFrames((prev) => [...prev, f] as StreamFrame[]))
    return () => unsubscribe()
  }, [subscribe, run_id])

  const ohlcData: CandlestickData[] = useMemo(() => (
    frames
      .filter((f) => f.ohlc)
      .map((f) => ({
        time: (new Date(f.ts).getTime() / 1000) as any,
        open: f.ohlc!.o ?? 0,
        high: f.ohlc!.h ?? 0,
        low: f.ohlc!.l ?? 0,
        close: f.ohlc!.c ?? 0,
      }))
  ), [frames])

  const equityData: LineData[] = useMemo(() => (
    frames
      .filter((f) => f.equity)
      .map((f) => ({ time: (new Date(f.ts).getTime() / 1000) as any, value: f.equity!.value }))
  ), [frames])

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
      <div className="flex items-center justify-between">
        <PlaybackControls playing={state.playing} speed={state.speed} onPlay={onPlay} onPause={onPause} onSpeedChange={onSpeedChange} />
        <div className="text-slate-500">Transport: {state.status} · Frames: {frames.length} · Dropped: {state.dropped}{state.status==='ws' && state.playing && frames.length===0 ? ' · No frames yet…' : ''}</div>
      </div>
      <div className="grid grid-cols-1 gap-4">
        <ChartOHLC data={ohlcData} formatTime={formatTime} />
        <EquityChart data={equityData} formatTime={formatTime} />
      </div>
    </div>
  )
}

export default RunPlayerContainer

