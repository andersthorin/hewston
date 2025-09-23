import type { StreamFrame } from './api'

export type PlayerTransport = {
  start: () => void
  pause: () => void
  setSpeed: (s: number) => void
  seek: (isoTs: string) => void
  onFrame: (cb: (f: StreamFrame) => void) => void
  onError: (cb: (e: any) => void) => void
  dispose: () => void
}

export function wsTransport(run_id: string, base = ''): PlayerTransport {
  let ws: WebSocket | null = null
  let frameCb: ((f: StreamFrame) => void) | null = null
  let errCb: ((e: any) => void) | null = null

  const url = (base || '').startsWith('ws')
    ? `${base}/backtests/${run_id}/ws`
    : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/backtests/${run_id}/ws`

  ws = new WebSocket(url)
  ws.onopen = () => {
    ws?.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
  }
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (msg.t === 'frame' && frameCb) frameCb(msg as StreamFrame)
    } catch (e) {
      // ignore
    }
  }
  ws.onerror = (e) => errCb?.(e)

  return {
    start() { ws?.send(JSON.stringify({ t: 'ctrl', cmd: 'play' })) },
    pause() { ws?.send(JSON.stringify({ t: 'ctrl', cmd: 'pause' })) },
    setSpeed(s: number) { ws?.send(JSON.stringify({ t: 'ctrl', cmd: 'speed', speed: s })) },
    seek(iso: string) { ws?.send(JSON.stringify({ t: 'ctrl', cmd: 'seek', ts: iso })) },
    onFrame(cb) { frameCb = cb },
    onError(cb) { errCb = cb },
    dispose() { ws?.close(); ws = null },
  }
}

export function sseTransport(run_id: string, speed = 60, base = ''): PlayerTransport {
  let es: EventSource | null = null
  let frameCb: ((f: StreamFrame) => void) | null = null
  let errCb: ((e: any) => void) | null = null

  const url = base
    ? `${base}/backtests/${run_id}/stream?speed=${speed}`
    : `/backtests/${run_id}/stream?speed=${speed}`
  es = new EventSource(url)
  es.addEventListener('frame', (ev) => {
    try {
      const msg = JSON.parse((ev as MessageEvent).data)
      if (msg.t === 'frame' && frameCb) frameCb(msg as StreamFrame)
    } catch (e) { /* ignore */ }
  })
  es.onerror = (e) => errCb?.(e)

  return {
    start() {},
    pause() {},
    setSpeed(_s: number) {},
    seek(_iso: string) {},
    onFrame(cb) { frameCb = cb },
    onError(cb) { errCb = cb },
    dispose() { es?.close(); es = null },
  }
}

