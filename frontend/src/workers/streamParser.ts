/// <reference lib="webworker" />
import { StreamFrameSchema, type StreamFrameT } from '../schemas/stream'
import type { WorkerInMessage, WorkerOutMessage } from '../types/streaming'

// Worker message types for stream parsing
type InMsg = WorkerInMessage
type OutMsg = WorkerOutMessage

let dropped = 0

let seen = 0
function handleFrame(payload: unknown) {
  const parsed = StreamFrameSchema.safeParse(payload)
  if (!parsed.success) {
    // drop invalid
    if (seen < 50) {
      const obj: any = payload && typeof payload === 'object' ? (payload as any) : null
      const keys = obj ? Object.keys(obj) : []
      const hasTs = !!(obj && (obj.ts || obj?.equity?.ts))
      console.debug('[worker] drop invalid frame', { t: obj?.t, hasTs, keys, errors: parsed.error?.errors, sample: obj })
    }
    return
  }
  let f = parsed.data as any
  // Fill missing ts from equity.ts if needed
  if (!f.ts && f?.equity?.ts) {
    f = { ...f, ts: f.equity.ts }
  }
  seen += 1
  if (seen <= 50) {
    try { console.debug('[worker] handleFrame', { n: seen, ts: (f as any)?.equity?.ts || (f as any)?.ts }) } catch {}
  }
  // Attach cumulative dropped count from the worker perspective
  const baseDropped = (f as any)?.dropped ?? 0
  const withDropped: StreamFrameT = { ...f, dropped: baseDropped + dropped }
  const message: OutMsg = { type: 'frame', data: withDropped }
  // Emit immediately to avoid any timer throttling in background tabs
  postMessage(message)
  if (seen <= 50) {
    try { console.debug('[worker] postMessage', { n: seen }) } catch {}
  }
}

self.onmessage = (ev: MessageEvent<InMsg>) => {
  const msg = ev.data
  switch (msg.type) {
    case 'init': {
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

