import React, { useSyncExternalStore, createContext, useContext } from 'react'
import type { StreamFrameT } from '../schemas/stream'

export type PlaybackRange = { start: string | null; end: string | null }
export type PlaybackState = {
  currentSimTime: string | null
  range: PlaybackRange
  playing: boolean
  frame: StreamFrameT | null
  markers: string[] // ISO timestamps for timeline markers (orders)
  markersMeta?: Array<{ ts: string; sym?: string }>
  focusedSymbol: string | null
  symbolsSeen: string[]
}

export type PlaybackStore = {
  // state accessors
  getState: () => PlaybackState
  subscribe: (cb: () => void) => () => void
  // mutations (internal)
  _setFrame: (f: StreamFrameT) => void
  _setPlaying: (p: boolean) => void
  _setRange: (r: PlaybackRange) => void
  _addMarkers: (isoTs: string[]) => void
  _addSymbols: (symbols: string[]) => void
  setFocus: (symbol: string | null) => void
  // controls (wired by container)
  play: () => void
  pause: () => void
  seek: (isoTs: string) => void
  setControls: (c: { play: () => void; pause: () => void; seek: (ts: string) => void }) => void
}

const initial: PlaybackState = {
  currentSimTime: null,
  range: { start: null, end: null },
  playing: false,
  frame: null,
  markers: [],
  markersMeta: [],
  focusedSymbol: null,
  symbolsSeen: [],
}

function createPlaybackStore(): PlaybackStore {
  let state: PlaybackState = { ...initial }
  const subs = new Set<() => void>()
  let controls: { play: () => void; pause: () => void; seek: (ts: string) => void } | null = null

  const emit = () => subs.forEach((cb) => cb())

  const store: PlaybackStore = {
    getState: () => state,
    subscribe: (cb) => { subs.add(cb); return () => subs.delete(cb) },
    _setFrame: (f) => {
      state = {
        ...state,
        frame: f,
        currentSimTime: (f?.equity?.ts || f?.ts) ?? state.currentSimTime,
      }
      // accumulate markers from orders if present
      if (Array.isArray(f?.orders) && f.orders.length > 0) {
        const newMarks = f.orders.map((o: any) => (o.ts_utc || o.ts || f.ts)).filter(Boolean)
        if (newMarks.length) {
          state = { ...state, markers: dedupeAppend(state.markers, newMarks) }
        }
        // collect symbols seen in orders
        const syms = f.orders.map((o: any) => (o.symbol || o.sym || o.instrument || o.inst || null)).filter(Boolean)
        if (syms.length) {
          state = { ...state, symbolsSeen: dedupeAppendStr(state.symbolsSeen, syms) }
        }
        // attach markers meta with symbol info
        const metas = f.orders.map((o: any) => {
          const ts = (o.ts_utc || o.ts || f.ts)
          if (!ts) return null
          const sym = (o.symbol || o.sym || o.instrument || o.inst || undefined)
          return { ts, sym }
        }).filter(Boolean) as Array<{ ts: string; sym?: string }>
        if (metas.length) {
          state = { ...state, markersMeta: dedupeAppendMeta(state.markersMeta || [], metas) }
        }
      }
      emit()
    },
    _setPlaying: (p) => { state = { ...state, playing: p }; emit() },
    _setRange: (r) => { state = { ...state, range: r }; emit() },
    _addMarkers: (ts) => { state = { ...state, markers: dedupeAppend(state.markers, ts) }; emit() },
    _addSymbols: (syms) => { state = { ...state, symbolsSeen: dedupeAppendStr(state.symbolsSeen, syms) }; emit() },
    setFocus: (sym) => { state = { ...state, focusedSymbol: sym }; emit() },
    play: () => { controls?.play?.() },
    pause: () => { controls?.pause?.() },
    seek: (ts) => { controls?.seek?.(ts) },
    setControls: (c) => { controls = c },
  }
  return store
}

function dedupeAppend(existing: string[], add: string[]): string[] {
  const set = new Set(existing)
  for (const t of add) set.add(t)
  return Array.from(set).sort()
}
function dedupeAppendStr(existing: string[], add: string[]): string[] {
  const set = new Set(existing)
  for (const s of add) set.add(s)
  return Array.from(set).sort()
}
function dedupeAppendMeta(existing: Array<{ ts: any; sym?: string }>, add: Array<{ ts: any; sym?: string }>): Array<{ ts: any; sym?: string }>{
  const key = (m: { ts: any; sym?: string }) => `${String(m.ts)}|${m.sym ?? ''}`
  const map = new Map(existing.map((m) => [key(m), m] as const))
  for (const m of add) map.set(key(m), m)
  return Array.from(map.values()).sort((a, b) => String(a.ts).localeCompare(String(b.ts)))
}

// Singleton store and React helpers
const playbackStore = createPlaybackStore()
const Ctx = createContext<PlaybackStore | null>(null)

export function PlaybackProvider({ children }: { children: React.ReactNode }) {
  return React.createElement(Ctx.Provider, { value: playbackStore }, children)
}

export function usePlaybackStore(): PlaybackStore {
  return useContext(Ctx) ?? playbackStore
}

export function usePlaybackSelector<T>(selector: (s: PlaybackState) => T): T {
  const store = usePlaybackStore()
  return useSyncExternalStore(store.subscribe, () => selector(store.getState()))
}

// Convenience selectors
export const selectors = {
  currentTs: (s: PlaybackState) => s.currentSimTime,
  range: (s: PlaybackState) => s.range,
  playing: (s: PlaybackState) => s.playing,
  frame: (s: PlaybackState) => s.frame,
  markers: (s: PlaybackState) => s.markers,
  markersMeta: (s: PlaybackState) => (s as any).markersMeta ?? [],
  focusedSymbol: (s: PlaybackState) => (s as any).focusedSymbol ?? null,
  symbolsSeen: (s: PlaybackState) => (s as any).symbolsSeen ?? [],
  filteredMarkers: (() => {
    // Memoize by reference to avoid useSyncExternalStore getSnapshot churn
    let lastFocus: string | null = null
    let lastMetaRef: Array<{ ts: string; sym?: string }> | null = null
    let lastResult: string[] = []
    return (s: PlaybackState) => {
      const focus = (s as any).focusedSymbol ?? null
      const metas = ((s as any).markersMeta ?? []) as Array<{ ts: string; sym?: string }>
      if (metas && metas.length) {
        if (metas === lastMetaRef && focus === lastFocus) {
          return lastResult
        }
        const filtered = focus ? metas.filter((m) => m.sym === focus) : metas
        lastResult = Array.from(new Set(filtered.map((m) => m.ts))).sort()
        lastMetaRef = metas
        lastFocus = focus
        return lastResult
      }
      // Fallback to plain markers; this array reference comes from state
      lastMetaRef = metas
      lastFocus = focus
      lastResult = s.markers
      return lastResult
    }
  })(),
}

export default playbackStore

