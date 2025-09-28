import { useCallback, useEffect, useRef, useState } from 'react'
import type { StreamFrameT } from '../schemas/stream'
import type { WorkerOutMessage } from '../types/streaming'
import { createWebSocketManager, type BFFWebSocketManager, type WebSocketHealth } from './websocket'
import { featureFlagService } from './featureFlags'

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
  // Enhanced with BFF health information
  health?: WebSocketHealth
  connectionSource?: 'bff' | 'backend'
}

export type Subscription = (f: StreamFrameT) => void

export function useRunPlayback(runId: string) {
  const [state, setState] = useState<PlaybackState>({
    status: 'idle',
    playing: false,
    speed: 60,
    dropped: 0,
    connectionSource: featureFlagService.isFeatureFlagEnabled('websocket') ? 'bff' : 'backend'
  })
  const subsRef = useRef<Set<Subscription>>(new Set())
  const workerRef = useRef<Worker | null>(null)
  const wsManagerRef = useRef<BFFWebSocketManager | null>(null)
  const framesSeenRef = useRef<number>(0)
  const playRetryTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const notify = useCallback((f: StreamFrameT) => {
    subsRef.current.forEach((cb) => cb(f))
    setState((s) => ({ ...s, dropped: f.dropped }))
  }, [])

  const updateHealthInfo = useCallback((health: WebSocketHealth) => {
    setState((s) => ({
      ...s,
      health,
      connectionSource: health.connectionSource,
      dropped: health.droppedFrames || s.dropped
    }))
  }, [])

  useEffect(() => {
    // Initialize worker
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

    // Initialize BFF-aware WebSocket manager
    const wsManager = createWebSocketManager(runId, {
      autoReconnect: true,
      maxReconnectAttempts: 5,
      reconnectDelay: 500,
      maxReconnectDelay: 5000,
      enableMessageQueue: true,
      maxQueueSize: 50,
      connectionTimeout: 10000,
    })
    wsManagerRef.current = wsManager

    let closed = false

    const startPlayKeepalive = () => {
      if (playRetryTimerRef.current) { clearInterval(playRetryTimerRef.current); playRetryTimerRef.current = null }
      playRetryTimerRef.current = setInterval(() => {
        if (!wsManager.isReady()) return
        if (framesSeenRef.current > 0) return
        try {
          wsManager.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
          devLog('play.sent', { runId, reason: 'keepalive' })
        } catch (error) {
          console.warn('Failed to send keepalive play command:', error)
        }
      }, 1000)
    }

    // Setup WebSocket manager event listeners
    const unsubscribeOpen = wsManager.addEventListener('open', () => {
      framesSeenRef.current = 0
      devLog('ws.open', { runId, source: wsManager.getHealth().connectionSource })
      setState((s) => ({ ...s, status: 'ws', playing: true }))
      updateHealthInfo(wsManager.getHealth())

      try {
        wsManager.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
        devLog('play.sent', { runId, reason: 'open' })
      } catch (error) {
        console.warn('Failed to send initial play command:', error)
      }
      startPlayKeepalive()
    })

    const unsubscribeMessage = wsManager.addEventListener('message', (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.t === 'frame') {
          devLog('frame.ts', msg.ts)
          worker.postMessage({ type: 'frame', payload: msg })
        }
        // ignore hb and echo
      } catch (error) {
        console.warn('Failed to parse WebSocket message:', error)
      }
    })

    const unsubscribeClose = wsManager.addEventListener('close', () => {
      if (playRetryTimerRef.current) {
        clearInterval(playRetryTimerRef.current)
        playRetryTimerRef.current = null
      }
      setState((s) => ({ ...s, status: 'error', playing: false }))
      updateHealthInfo(wsManager.getHealth())
    })

    const unsubscribeError = wsManager.addEventListener('error', (error: Event) => {
      console.warn('WebSocket error:', error)
      setState((s) => ({ ...s, status: 'error', playing: false }))
      updateHealthInfo(wsManager.getHealth())
    })

    const unsubscribeStateChange = wsManager.addEventListener('stateChange', () => {
      updateHealthInfo(wsManager.getHealth())
    })

    const unsubscribeHealthUpdate = wsManager.addEventListener('healthUpdate', (health: WebSocketHealth) => {
      updateHealthInfo(health)
    })

    const connect = () => {
      if (closed) return
      setState((s) => ({ ...s, status: 'connecting' }))

      wsManager.connect().catch(error => {
        console.warn('WebSocket connection failed:', error)
        setState((s) => ({ ...s, status: 'error', playing: false }))
      })
    }

    connect()

    return () => {
      closed = true

      // Cleanup event listeners
      unsubscribeOpen()
      unsubscribeMessage()
      unsubscribeClose()
      unsubscribeError()
      unsubscribeStateChange()
      unsubscribeHealthUpdate()

      // Cleanup timers
      if (playRetryTimerRef.current) {
        clearInterval(playRetryTimerRef.current)
        playRetryTimerRef.current = null
      }

      // Close WebSocket manager
      if (wsManagerRef.current) {
        wsManagerRef.current.close()
        wsManagerRef.current = null
      }

      // Terminate worker
      if (workerRef.current) {
        workerRef.current.terminate()
        workerRef.current = null
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId])

  const subscribe = useCallback((cb: Subscription) => {
    subsRef.current.add(cb)
    return () => { subsRef.current.delete(cb) }
  }, [])

  const onPlay = useCallback(() => {
    wsManagerRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
    setState((s) => ({ ...s, playing: true }))
  }, [])

  const onPause = useCallback(() => {
    wsManagerRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'pause' }))
    setState((s) => ({ ...s, playing: false }))
  }, [])

  const onSpeedChange = useCallback((spd: number) => {
    setState((s) => ({ ...s, speed: spd }))
    wsManagerRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'speed', speed: spd }))
  }, [])

  const onSeek = useCallback((isoTs: string) => {
    wsManagerRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'seek', ts: isoTs }))
  }, [])

  // Additional BFF-specific functions
  const getConnectionHealth = useCallback(() => {
    return wsManagerRef.current?.getHealth() || null
  }, [])

  const reconnect = useCallback(() => {
    return wsManagerRef.current?.reconnect()
  }, [])

  const ping = useCallback(() => {
    wsManagerRef.current?.ping()
  }, [])

  return {
    state,
    subscribe,
    onPlay,
    onPause,
    onSpeedChange,
    onSeek,
    // Enhanced BFF functions
    getConnectionHealth,
    reconnect,
    ping
  }
}

