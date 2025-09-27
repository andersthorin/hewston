import { useCallback, useEffect, useRef, useState } from 'react'
import type { StreamFrameT } from '../schemas/stream'
import type { WorkerOutMessage } from '../types/streaming'

// Dev logging helper (only logs in Vite dev)
const devLog = (...args: unknown[]) => {
  try {
    if ((import.meta as { env?: { DEV?: boolean } }).env?.DEV) {
      console.debug('[run-ws]', ...args)
    }
  } catch (error) {
    console.warn('Failed to log debug message:', error)
  }
}

export type PlaybackState = {
  status: 'idle' | 'connecting' | 'ws' | 'sse' | 'ended' | 'error'
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
  const framesSeenRef = useRef<number>(0)
  const playRetryTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const notify = useCallback((f: StreamFrameT) => {
    subsRef.current.forEach((cb) => cb(f))
    setState((s) => ({ ...s, dropped: f.dropped }))
  }, [])

  useEffect(() => {
    // init worker
    const worker = new Worker(new URL('../workers/streamParser.ts', import.meta.url), { type: 'module' })
    worker.postMessage({ type: 'init', fps: 30 })
    worker.onmessage = (ev: MessageEvent<WorkerOutMessage>) => {
      const msg = ev.data
      if (msg.type === 'frame') {
        framesSeenRef.current += 1
        notify(msg.data as StreamFrameT)
        // Stop keep-alive play retries after first frame
        if (playRetryTimerRef.current) { clearInterval(playRetryTimerRef.current); playRetryTimerRef.current = null }
      } else if (msg.type === 'error') {
        console.warn('Worker error:', msg.error)
        setState((s) => ({ ...s, status: 'error', playing: false }))
      } else if (msg.type === 'ready') {
        console.debug('Worker ready')
      }
    }
    workerRef.current = worker

    let reconnectAttempts = 0
    let closed = false
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    const startPlayKeepalive = () => {
      if (playRetryTimerRef.current) { clearInterval(playRetryTimerRef.current); playRetryTimerRef.current = null }
      playRetryTimerRef.current = setInterval(() => {
        const ws = wsRef.current
        if (!ws || ws.readyState !== WebSocket.OPEN) return
        if (framesSeenRef.current > 0) return
        try {
          ws.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
          devLog('play.sent', { runId, reason: 'keepalive' })
        } catch (error) {
          console.warn('Failed to send keepalive play command:', error)
        }
      }, 1000)
    }

    const connect = () => {
      if (closed) return
      setState((s) => ({ ...s, status: 'connecting' }))
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const wsUrl = `${proto}://${location.host}/backtests/${runId}/ws`
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        reconnectAttempts = 0
        framesSeenRef.current = 0
        devLog('ws.open', { runId })
        setState((s) => ({ ...s, status: 'ws', playing: true }))
        try {
          ws.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
          devLog('play.sent', { runId, reason: 'open' })
        } catch (error) {
          console.warn('Failed to send initial play command:', error)
        }
        startPlayKeepalive()
      }
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.t === 'frame') { devLog('frame.ts', msg.ts); worker.postMessage({ type: 'frame', payload: msg }) }
          // ignore hb and echo
        } catch (error) {
          console.warn('Failed to parse WebSocket message:', error)
        }
      }

      const scheduleReconnect = () => {
        if (closed) return
        if (playRetryTimerRef.current) { clearInterval(playRetryTimerRef.current); playRetryTimerRef.current = null }
        const delay = Math.min(500 * Math.pow(2, reconnectAttempts++), 5000)
        devLog('ws.scheduleReconnect', { runId, delay })
        reconnectTimer = setTimeout(connect, delay)
      }
      ws.onerror = () => scheduleReconnect()
      ws.onclose = () => scheduleReconnect()
    }

    connect()

    return () => {
      closed = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (playRetryTimerRef.current) { clearInterval(playRetryTimerRef.current); playRetryTimerRef.current = null }
      const ws = wsRef.current
      if (ws) {
        const rs = ws.readyState
        if (rs === WebSocket.OPEN || rs === WebSocket.CLOSING) {
          try {
            ws.close()
          } catch (error) {
            console.warn('Failed to close WebSocket:', error)
          }
        }
      }
      wsRef.current = null
      worker.terminate(); workerRef.current = null
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

