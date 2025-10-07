import { useEffect, useMemo, useRef } from 'react'
import type { CandlestickChartAPI } from '../types/charts'
import { usePlaybackSelector, selectors } from '../store/playbackClock'

export default function OverlaysOrders({
  chartRef,
}: {
  chartRef: React.MutableRefObject<CandlestickChartAPI | null>
}) {
  const frame = usePlaybackSelector(selectors.frame)
  const focus = usePlaybackSelector(selectors.focusedSymbol)

  type OrderMarker = {
    time: string
    position: string
    color: string
    shape: string
    text: string
    price?: number
  }
  const accRef = useRef<Map<string, OrderMarker>>(new Map())

  const filtered = useMemo(() => {
    const orders = frame?.orders ?? []
    type OrderLike = {
      symbol?: string
      sym?: string
      instrument?: string
      inst?: string
      ts_utc?: unknown
      ts?: unknown
      order_id?: unknown
      price?: unknown
      side?: unknown
    }
    return orders.filter((o) => {
      const ord = o as OrderLike
      if (!focus) return true
      const sym = ord.symbol || ord.sym || ord.instrument || ord.inst
      return sym ? sym === focus : false
    })
  }, [frame, focus])

  useEffect(() => {
    const acc = accRef.current
    for (const o of filtered) {
      const ts = o.ts_utc || o.ts || frame?.ts
      if (!ts) continue
      const sym = o.symbol || o.sym || o.instrument || o.inst || ''
      const key = `${ts}|${sym}|${o.order_id || ''}`
      if (acc.has(key)) continue
      const price = typeof o.price === 'number' ? o.price : undefined
      const side = (o.side || '').toString().toLowerCase()
      const color = side.includes('buy') || side.includes('long') ? '#16a34a' : '#dc2626'
      const position = side.includes('buy') || side.includes('long') ? 'belowBar' : 'aboveBar'
      // Derive a safe 'YYYY-MM-DD' day string from various timestamp shapes
      const day = (() => {
        try {
          if (typeof ts === 'string') {
            // Fast path for ISO-like strings
            if (ts.length >= 10) return ts.slice(0, 10)
            const d = new Date(ts)
            if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0, 10)
            return null
          }
          if (typeof ts === 'number' && Number.isFinite(ts)) {
            // Heuristic: treat <1e12 as seconds, otherwise ms
            const ms = ts < 1e12 ? ts * 1000 : ts
            const d = new Date(ms)
            if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0, 10)
            return null
          }
          if (ts instanceof Date) {
            if (!Number.isNaN(ts.getTime())) return ts.toISOString().slice(0, 10)
            return null
          }
          const s = ts?.toString?.()
          if (s && s.length >= 10) return s.slice(0, 10)
          return null
        } catch {
          return null
        }
      })()
      if (!day) continue
      acc.set(key, {
        time: day,
        position,
        color,
        shape: 'arrowUp',
        text: side.startsWith('b') ? 'B' : 'S',
        price,
      })
    }
    const markers = Array.from(acc.values())
    chartRef.current?.setMarkers(markers)
  }, [filtered, chartRef, frame?.ts])

  return null
}
