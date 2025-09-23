/// <reference lib="webworker" />
import { StreamFrameSchema, type StreamFrameT } from '../schemas/stream'

// Messages from main thread
// { type: 'init', fps?: number }
// { type: 'frame', payload: any }
// { type: 'hb' } | { type: 'end' } | { type: 'err', error?: any }

type InMsg =
  | { type: 'init'; fps?: number }
  | { type: 'frame'; payload: unknown }
  | { type: 'hb' }
  | { type: 'end' }
  | { type: 'err'; error?: any }


let queue: StreamFrameT[] = []
let dropped = 0
let intervalId: number | null = null
let targetMs = 1000 / 30

function startTicker(fps: number | undefined) {
  if (intervalId) clearInterval(intervalId)
  targetMs = 1000 / (fps && fps > 0 ? fps : 30)
  intervalId = setInterval(() => tick(), Math.max(16, targetMs)) as unknown as number
}

function tick() {
  if (queue.length === 0) return
  const frame = queue.shift()!
  ;(postMessage as any)({ type: 'frame', frame })
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
    case 'init':
      startTicker(msg.fps)
      break
    case 'frame':
      handleFrame(msg.payload)
      break
    case 'hb':
      ;(postMessage as any)({ type: 'hb' })
      break
    case 'end':
      ;(postMessage as any)({ type: 'end' })
      break
    case 'err':
      ;(postMessage as any)({ type: 'err', error: String(msg.error ?? '') })
      break
  }
}

