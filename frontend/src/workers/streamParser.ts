/// <reference lib="webworker" />
import { StreamFrameSchema, type StreamFrameT } from '../schemas/stream'
import type { WorkerInMessage, WorkerOutMessage } from '../types/streaming'

// Worker message types for stream parsing
type InMsg = WorkerInMessage
type OutMsg = WorkerOutMessage

const dropped = 0

let seen = 0
let lastOutTs = 0
function handleFrame(payload: unknown) {
  const tParse0 = performance.now()
  const parsed = StreamFrameSchema.safeParse(payload)
  const tParse1 = performance.now()
  if (!parsed.success) {
    // drop invalid
    if (seen < 50) {
      const obj =
        payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : null
      const keys = obj ? Object.keys(obj) : []
      const hasTs = !!(obj && (obj.ts || (obj.equity as Record<string, unknown> | undefined)?.ts))
      console.debug('[worker] drop invalid frame', {
        t: obj?.t,
        hasTs,
        keys,
        issues: parsed.error?.issues,
        sample: obj,
      })
    }
    return
  }
  let f: StreamFrameT = parsed.data
  // Fill missing ts from equity.ts if needed
  if (!f.ts && f?.equity?.ts) {
    f = { ...f, ts: f.equity.ts }
  }
  seen += 1
  if (seen <= 50) {
    try {
      const parseMs = +(tParse1 - tParse0).toFixed(2)
      console.debug('[worker] handleFrame', {
        n: seen,
        ts: f?.equity?.ts || f?.ts,
        parse_ms: parseMs,
      })
      if (parseMs > 5) {
        // eslint-disable-next-line no-console
        console.debug('[diag][worker.parse_ms]', { ms: parseMs })
      }
    } catch {
      // Ignore logging errors
    }
  }
  // Attach cumulative dropped count from the worker perspective
  const baseDropped = f?.dropped ?? 0
  const withDropped: StreamFrameT = { ...f, dropped: baseDropped + dropped }
  const message: OutMsg = { type: 'frame', data: withDropped }
  // Emit immediately to avoid any timer throttling in background tabs
  // Diagnostics: worker out delta
  try {
    const now = Date.now()
    const dt = lastOutTs ? now - lastOutTs : 0
    lastOutTs = now
    // eslint-disable-next-line no-console
    console.debug('[diag][worker.out]', { dt })
  } catch {}
  postMessage(message)
  if (seen <= 50) {
    try {
      console.debug('[worker] postMessage', { n: seen })
    } catch {
      // Ignore logging errors
    }
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
      const errorMessage: OutMsg = {
        type: 'error',
        error: String(msg.error ?? 'Unknown worker error'),
      }
      postMessage(errorMessage)
      break
    }
  }
}
