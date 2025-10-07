import { useCallback, useEffect, useRef, useState } from 'react'
import type { StreamFrameT } from '../schemas/stream'
import type { WorkerOutMessage } from '../types/streaming'
import { createWebSocketManager, type BFFWebSocketManager, type WebSocketHealth } from './websocket'
import { featureFlagService } from './featureFlags'
import { DEFAULT_FPS } from '../constants'

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

export function useBacktestPlayback(backtestId: string) {
  const [state, setState] = useState<PlaybackState>({
    status: 'idle',
    playing: false,
    speed: 60,
    dropped: 0,
    connectionSource: featureFlagService.isFeatureFlagEnabled('websocket') ? 'bff' : 'backend',
  })
  const subsRef = useRef<Set<Subscription>>(new Set())
  const workerRef = useRef<Worker | null>(null)
  const wsManagerRef = useRef<BFFWebSocketManager | null>(null)
  const framesSeenRef = useRef<number>(0)
  // TEMP DEBUG: limit first 20 raw WS frame logs
  const feRawDebugRef = useRef<number>(0)

  // Buffered smooth-render state
  const frameBufferRef = useRef<StreamFrameT[]>([])
  const lastPaintRef = useRef<number>(0)
  const rafIdRef = useRef<number | null>(null)
  const targetMsRef = useRef<number>(Math.max(16, Math.round(1000 / DEFAULT_FPS)))
  const playingRef = useRef<boolean>(false)
  // Diagnostics timing refs
  const lastWsRawTimeRef = useRef<number>(0)
  const lastWorkerOutTimeRef = useRef<number>(0)
  const lastConsumeTimeRef = useRef<number>(0)

  const notify = useCallback((f: StreamFrameT) => {
    if (framesSeenRef.current <= 20) {
      try {
        // eslint-disable-next-line no-console
        console.debug('[notify->subs]', {
          n: framesSeenRef.current,
          ts: (f as any)?.equity?.ts || (f as any)?.ts,
        })
      } catch {}
    }
    subsRef.current.forEach((cb) => cb(f))
    setState((s) => ({ ...s, dropped: (f as any).dropped ?? s.dropped }))
  }, [])

  const updateHealthInfo = useCallback((health: WebSocketHealth) => {
    setState((s) => ({
      ...s,
      health,
      connectionSource: health.connectionSource,
      dropped: health.droppedFrames ?? s.dropped,
    }))
  }, [])

  useEffect(() => {
    // Initialize worker
    const worker = new Worker(new URL('../workers/streamParser.ts', import.meta.url), {
      type: 'module',
    })
    worker.postMessage({ type: 'init', fps: DEFAULT_FPS })
    worker.onmessage = (ev: MessageEvent<WorkerOutMessage>) => {
      const msg = ev.data
      if (msg.type === 'frame') {
        framesSeenRef.current += 1
        if (framesSeenRef.current <= 20) {
          try {
            // eslint-disable-next-line no-console
            console.debug('[fe-worker->main]', {
              n: framesSeenRef.current,
              ts: (msg.data as any)?.equity?.ts || (msg.data as any)?.ts,
            })
          } catch {}
        }
        // Buffer frame and drop-oldest if buffer grows too large
        frameBufferRef.current.push(msg.data as StreamFrameT)
        if (frameBufferRef.current.length > 100) {
          frameBufferRef.current.splice(0, frameBufferRef.current.length - 100)
        }
        // Diagnostics: worker -> main delta and buffer size
        try {
          const now = Date.now()
          const dt = lastWorkerOutTimeRef.current ? now - lastWorkerOutTimeRef.current : 0
          lastWorkerOutTimeRef.current = now
          // eslint-disable-next-line no-console
          console.debug('[diag][worker.out]', { dt, buf: frameBufferRef.current.length })
        } catch {}
      } else if (msg.type === 'error') {
        console.warn('Worker error:', msg.error)
        setState((s) => ({ ...s, status: 'error', playing: false }))
      } else if (msg.type === 'ready') {
        console.debug('Worker ready')
      }
    }
    // Capture worker fatal errors (outside its postMessage protocol)
    worker.addEventListener('error', (e) => {
      try {
        console.error('[worker.onerror]', e.message || e)
      } catch {}
      setState((s) => ({ ...s, status: 'error', playing: false }))
    })
    worker.addEventListener('messageerror', (e) => {
      try {
        console.error('[worker.messageerror]', e.data)
      } catch {}
    })
    workerRef.current = worker

    // Initialize BFF-aware WebSocket manager
    const wsManager = createWebSocketManager(backtestId, {
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

    // Setup WebSocket manager event listeners
    const unsubscribeOpen = wsManager.addEventListener('open', () => {
      framesSeenRef.current = 0
      devLog('ws.open', { backtestId, source: wsManager.getHealth().connectionSource })
      setState((s) => ({ ...s, status: 'ws', playing: false })) // Don't auto-play, wait for ready signal
      updateHealthInfo(wsManager.getHealth())

      // Don't send play command here - wait for frontend to send ready signal
      devLog('ws.connected', { backtestId, reason: 'waiting_for_ready_signal' })
    })

    const unsubscribeMessage = wsManager.addEventListener('message', (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.t === 'frame') {
          // Diagnostics: raw WS arrival delta
          try {
            const now = Date.now()
            const dt = lastWsRawTimeRef.current ? now - lastWsRawTimeRef.current : 0
            lastWsRawTimeRef.current = now
            const ts = msg.ts || msg?.equity?.ts
            // eslint-disable-next-line no-console
            console.debug('[diag][ws.raw]', { dt, ts })
          } catch {}

          // TEMP DEBUG: log first 20 raw frames from WS before any transformation
          if (feRawDebugRef.current < 20) {
            try {
              const ts = msg.ts || msg?.equity?.ts
              const eq = msg?.equity?.value
              // eslint-disable-next-line no-console
              console.debug('[fe-ws-raw]', { n: feRawDebugRef.current + 1, ts, eq })
            } catch {}
            feRawDebugRef.current += 1
          }
          try {
            // eslint-disable-next-line no-console
            if (feRawDebugRef.current <= 20)
              console.debug('[main->worker] post frame', { n: feRawDebugRef.current })
            worker.postMessage({ type: 'frame', payload: msg })
          } catch (err) {
            console.error('Failed to post frame to worker', err)
          }
        } else if (msg.t === 'err') {
          console.warn('Stream error from server:', msg)
          setState((s) => ({ ...s, status: 'error', playing: false }))
        }
        // ignore hb and echo
      } catch (error) {
        console.warn('Failed to parse WebSocket message:', error)
      }
    })

    const unsubscribeClose = wsManager.addEventListener('close', () => {
      // Reflect manager state to avoid sticky 'error' during auto-reconnects
      const mgrState = wsManager.getState()
      const nextStatus: PlaybackState['status'] =
        mgrState === 'reconnecting' || mgrState === 'connecting' ? 'connecting' : 'error'
      setState((s) => ({ ...s, status: nextStatus, playing: false }))
      updateHealthInfo(wsManager.getHealth())
    })

    const unsubscribeError = wsManager.addEventListener('error', (error: Event) => {
      console.warn('WebSocket error:', error)
      // If auto-reconnect is enabled, show 'connecting' to avoid frozen/error UX
      const mgrState = wsManager.getState()
      const nextStatus: PlaybackState['status'] =
        mgrState === 'reconnecting' || mgrState === 'connecting' ? 'connecting' : 'error'
      setState((s) => ({ ...s, status: nextStatus, playing: false }))
      updateHealthInfo(wsManager.getHealth())
    })

    // Start render scheduler (decouple render cadence from arrival cadence)
    const startScheduler = () => {
      if (rafIdRef.current !== null) return
      const tick = (t: number) => {
        try {
          if (t - lastPaintRef.current >= targetMsRef.current) {
            if (playingRef.current && frameBufferRef.current.length) {
              const bufBefore = frameBufferRef.current.length
              const now = Date.now()
              const dt = lastConsumeTimeRef.current ? now - lastConsumeTimeRef.current : 0
              lastConsumeTimeRef.current = now
              const next = frameBufferRef.current.shift()!
              const bufAfter = frameBufferRef.current.length
              // eslint-disable-next-line no-console
              console.debug('[diag][raf.consume]', {
                dt,
                buf_before: bufBefore,
                buf_after: bufAfter,
              })
              notify(next)
            }
            lastPaintRef.current = t
          }
        } finally {
          rafIdRef.current = requestAnimationFrame(tick)
        }
      }
      rafIdRef.current = requestAnimationFrame(tick)
    }
    startScheduler()

    const unsubscribeStateChange = wsManager.addEventListener('stateChange', () => {
      updateHealthInfo(wsManager.getHealth())
    })

    const unsubscribeHealthUpdate = wsManager.addEventListener(
      'healthUpdate',
      (health: WebSocketHealth) => {
        updateHealthInfo(health)
      },
    )

    const connect = () => {
      if (closed) return
      setState((s) => ({ ...s, status: 'connecting' }))

      wsManager.connect().catch((error) => {
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

      // Cancel render scheduler
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = null
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
  }, [backtestId])

  // Keep a ref in sync with playing state (covers error/close transitions)
  useEffect(() => {
    playingRef.current = state.playing
  }, [state.playing])

  const subscribe = useCallback((cb: Subscription) => {
    subsRef.current.add(cb)
    return () => {
      subsRef.current.delete(cb)
    }
  }, [])

  const onPlay = useCallback(() => {
    wsManagerRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
    playingRef.current = true
    setState((s) => ({ ...s, playing: true }))
  }, [])

  const onPause = useCallback(() => {
    wsManagerRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'pause' }))
    playingRef.current = false
    setState((s) => ({ ...s, playing: false }))
  }, [])

  const onSpeedChange = useCallback((spd: number) => {
    setState((s) => ({ ...s, speed: spd }))
    wsManagerRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'speed', speed: spd }))
  }, [])

  const onSeek = useCallback((isoTs: string) => {
    wsManagerRef.current?.send(JSON.stringify({ t: 'ctrl', cmd: 'seek', ts: isoTs }))
  }, [])

  const sendReady = useCallback(() => {
    wsManagerRef.current?.send(JSON.stringify({ t: 'ready' }))
    // Auto-start playback when ready signal is sent
    playingRef.current = true
    setState((s) => ({ ...s, playing: true }))
    console.debug('[ws] ready signal sent to backend, autoplay enabled')
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
    sendReady,
    // Enhanced BFF functions
    getConnectionHealth,
    reconnect,
    ping,
  }
}
