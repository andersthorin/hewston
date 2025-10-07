import { useMemo } from 'react'
import { usePlaybackSelector, usePlaybackStore } from '../../store/playbackClock'

export default function SymbolFocus() {
  const store = usePlaybackStore()
  const focused = usePlaybackSelector(
    (s) => (s as { focusedSymbol?: string | null }).focusedSymbol ?? null,
  )
  const symbols = usePlaybackSelector(
    (s) => (s as { symbolsSeen?: string[] }).symbolsSeen ?? [],
  ) as string[]
  const options = useMemo(() => ['All', ...symbols], [symbols])

  const onChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const v = e.target.value
    store.setFocus(v === 'All' ? null : v)
  }

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm text-slate-600">Focus symbol</label>
      <select
        className="border rounded px-2 py-1 text-sm"
        value={focused ?? 'All'}
        onChange={onChange}
      >
        {options.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
    </div>
  )
}
