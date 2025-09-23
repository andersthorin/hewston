import { useCallback, useEffect, useRef, useState } from 'react'
import type { StreamFrameT } from '../schemas/stream'

export type PlaybackState = {
  status: 'idle' | 'ws' | 'sse' | 'ended' | 'error'
  playing: boolean
  speed: number
  dropped: number
}

export type Subscription = (f: StreamFrameT) => void

export function useRunPlayback(runId: string) {
  const [state, setState] = useState<PlaybackState>({ status: 'idle', playing: false, speed: 60, dropped: 0 })
  const subsRef = useRef<Set<Subscription>>(new Set())
  const workerRef = useRef<Worker | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const esRef = useRef<EventSource | null>(null)

  const notify = useCallback((f: StreamFrameT) => {
    subsRef.current.forEach((cb) => cb(f))
    setState((s) => ({ ...s, dropped: f.dropped }))
  }, [])

  useEffect(() => {
    // init worker
    const worker = new Worker(new URL('../workers/streamParser.ts', import.meta.url), { type: 'module' })
    worker.postMessage({ type: 'init', fps: 30 })
    worker.onmessage = (ev: MessageEvent<any>) => {
      const msg = ev.data
      if (msg.type === 'frame') notify(msg.frame as StreamFrameT)
      else if (msg.type === 'end') setState((s) => ({ ...s, status: 'ended', playing: false }))
      else if (msg.type === 'err') setState((s) => ({ ...s, status: 'error', playing: false }))
    }
    workerRef.current = worker

    // connect WS
    const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/backtests/${runId}/ws`
    const ws = new WebSocket(wsUrl)
    ws.onopen = () => { setState((s) => ({ ...s, status: 'ws', playing: true })); ws.send(JSON.stringify({ t: 'ctrl', cmd: 'play' })) }
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.t === 'frame') worker.postMessage({ type: 'frame', payload: msg })
      } catch { /* ignore */ }
    }
    ws.onerror = () => {
      // fallback to SSE
      setState((s) => ({ ...s, status: 'sse', playing: false }))
      const url = `/backtests/${runId}/stream?speed=${state.speed}`
      const es = new EventSource(url)
      es.onmessage = () => { /* default channel unused */ }
      es.addEventListener('frame', (ev) => {
        try { const msg = JSON.parse((ev as MessageEvent).data); worker.postMessage({ type: 'frame', payload: msg }) } catch {}
      })
      es.addEventListener('end', () => setState((s) => ({ ...s, status: 'ended', playing: false })))
      es.onerror = () => setState((s) => ({ ...s, status: 'error', playing: false }))
      esRef.current = es
    }
    wsRef.current = ws

    return () => {
      worker.terminate(); workerRef.current = null
      ws.close(); wsRef.current = null
      esRef.current?.close(); esRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId])

  const subscribe = useCallback((cb: Subscription) => {
    subsRef.current.add(cb)
    return () => { subsRef.current.delete(cb) }
  }, [])

  const onPlay = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
    setState((s) => ({ ...s, playing: true }))
  }, [])
  const onPause = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'pause' }))
    setState((s) => ({ ...s, playing: false }))
  }, [])
  const onSpeedChange = useCallback((spd: number) => {
    setState((s) => ({ ...s, speed: spd }))
    wsRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'speed', speed: spd }))
  }, [])
  const onSeek = useCallback((isoTs: string) => {
    wsRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'seek', ts: isoTs }))
  }, [])

  return { state, subscribe, onPlay, onPause, onSpeedChange, onSeek }
}

