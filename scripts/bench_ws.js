#!/usr/bin/env node
/*
 Measure WS playback jitter and FPS. Requires Node 22+ (global WebSocket).
 Usage: node scripts/bench_ws.js ws://127.0.0.1:8000/backtests/<run_id>/ws [durationSec]
*/
const url = process.argv[2]
const DURATION = Number(process.argv[3] || 10)
if (!url) {
  console.error('Usage: node scripts/bench_ws.js ws://host/backtests/<run_id>/ws [durationSec]')
  process.exit(2)
}

const times = []
let last = null
let frames = 0
let timer = null

const ws = new WebSocket(url)
ws.addEventListener('open', () => {
  ws.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
  timer = setTimeout(() => {
    ws.close()
  }, DURATION * 1000)
})
ws.addEventListener('message', (ev) => {
  try {
    const m = JSON.parse(ev.data)
    if (m.t === 'frame') {
      const now = Date.now()
      if (last !== null) times.push(now - last)
      last = now
      frames += 1
    }
  } catch {}
})
ws.addEventListener('close', () => {
  if (timer) clearTimeout(timer)
  if (times.length === 0) {
    console.log(JSON.stringify({ frames: 0, fps: 0, p50_ms: null, p95_ms: null }))
    return
  }
  times.sort((a,b)=>a-b)
  const p = (q)=>{const idx=Math.max(0,Math.min(times.length-1,Math.floor(q*times.length)));return times[idx]}
  const elapsed = times.reduce((a,b)=>a+b,0)
  const fps = frames / (elapsed/1000)
  const out = { frames, fps: Number(fps.toFixed(2)), p50_ms: p(0.5), p95_ms: p(0.95) }
  console.log(JSON.stringify(out))
})

