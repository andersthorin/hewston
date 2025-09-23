import { useEffect, useState } from 'react'
import type { StreamFrame } from '../services/api'
import { useRunPlayback } from '../services/ws'
import PlaybackControls from '../components/PlaybackControls'
import ChartOHLC from '../components/ChartOHLC'
import EquityChart from '../components/EquityChart'

export type RunPlayerContainerProps = { run_id: string }

export function RunPlayerContainer({ run_id }: RunPlayerContainerProps) {
  const [frames, setFrames] = useState<StreamFrame[]>([])
  const { state, subscribe, onPlay, onPause, onSpeedChange } = useRunPlayback(run_id)

  useEffect(() => {
    setFrames([])
    const unsubscribe = subscribe((f) => setFrames((prev) => [...prev, f] as StreamFrame[]))
    return () => unsubscribe()
  }, [subscribe, run_id])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <PlaybackControls playing={state.playing} speed={state.speed} onPlay={onPlay} onPause={onPause} onSpeedChange={onSpeedChange} />
        <div style={{ color: '#64748B' }}>Transport: {state.status} · Dropped: {state.dropped}</div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <ChartOHLC frames={frames} />
        <EquityChart frames={frames} />
      </div>
    </div>
  )
}

export default RunPlayerContainer

