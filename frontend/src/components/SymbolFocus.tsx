import { useMemo } from 'react'
import { usePlaybackSelector, usePlaybackStore } from '../store/playbackClock'

export default function SymbolFocus() {
  const store = usePlaybackStore()
  const focused = usePlaybackSelector((s) => (s as any).focusedSymbol ?? null)
  const symbols = usePlaybackSelector((s) => (s as any).symbolsSeen ?? []) as string[]
  const options = useMemo(() => ['All', ...symbols], [symbols])

  const onChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const v = e.target.value
    // @ts-ignore store may have setFocus
    store.setFocus?.(v === 'All' ? null : v)
  }

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm text-slate-600">Focus symbol</label>
      <select className="border rounded px-2 py-1 text-sm" value={focused ?? 'All'} onChange={onChange}>
        {options.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
    </div>
  )
}

