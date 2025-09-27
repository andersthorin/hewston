/// <reference lib="webworker" />
import { StreamFrameSchema, type StreamFrameT } from '../schemas/stream'
import { DEFAULT_FPS, STREAM_PARSER_TARGET_MS, MIN_FRAME_INTERVAL_MS } from '../constants'
import type { WorkerInMessage, WorkerOutMessage } from '../types/streaming'

// Worker message types for stream parsing
type InMsg = WorkerInMessage
type OutMsg = WorkerOutMessage

const queue: StreamFrameT[] = []
let dropped = 0
let intervalId: number | null = null
let targetMs = STREAM_PARSER_TARGET_MS

function startTicker(fps: number | undefined) {
  if (intervalId) clearInterval(intervalId)
  targetMs = 1000 / (fps && fps > 0 ? fps : DEFAULT_FPS)
  intervalId = setInterval(() => tick(), Math.max(MIN_FRAME_INTERVAL_MS, targetMs)) as unknown as number
}

function tick() {
  if (queue.length === 0) return
  const frame = queue.shift()!
  const message: OutMsg = { type: 'frame', data: frame }
  postMessage(message)
}

function handleFrame(payload: unknown) {
  const parsed = StreamFrameSchema.safeParse(payload)
  if (!parsed.success) {
    // drop invalid
    return
  }
  // Backpressure: cap queue size
  const MAX_Q = 120
  if (queue.length >= MAX_Q) {
    queue.shift()
    dropped += 1
  }
  const f = parsed.data
  // attach dropped cumulative from worker perspective
  const withDropped: StreamFrameT = { ...f, dropped: f.dropped + dropped }
  queue.push(withDropped)
}

self.onmessage = (ev: MessageEvent<InMsg>) => {
  const msg = ev.data
  switch (msg.type) {
    case 'init': {
      startTicker(msg.fps)
      const readyMessage: OutMsg = { type: 'ready' }
      postMessage(readyMessage)
      break
    }
    case 'frame':
      handleFrame(msg.payload)
      break
    case 'hb':
      // Heartbeat messages don't need to be forwarded in current implementation
      break
    case 'end':
      // End messages don't need to be forwarded in current implementation
      break
    case 'err': {
      const errorMessage: OutMsg = { type: 'error', error: String(msg.error ?? 'Unknown worker error') }
      postMessage(errorMessage)
      break
    }
  }
}

