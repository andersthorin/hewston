export type PlaybackControlsProps = {
  playing: boolean
  onPlay: () => void
  onPause: () => void
  speed?: number
  onSpeedChange?: (s: number) => void
  hideSpeed?: boolean
}

export function PlaybackControls({ playing, speed, onPlay, onPause, onSpeedChange, hideSpeed }: PlaybackControlsProps) {
  return (
    <div className="my-2 flex items-center gap-2">
      {playing ? (
        <button className="px-3 py-1 rounded bg-slate-800 text-white hover:bg-slate-700" onClick={onPause}>Pause</button>
      ) : (
        <button className="px-3 py-1 rounded bg-slate-800 text-white hover:bg-slate-700" onClick={onPlay}>Play</button>
      )}
      {!hideSpeed && speed !== undefined && onSpeedChange ? (
        <label className="inline-flex items-center gap-1 text-slate-600">
          <span>Speed:</span>
          <select className="px-2 py-1 border border-slate-300 rounded" value={speed} onChange={(e) => onSpeedChange(Number(e.target.value))}>
            <option value={30}>30</option>
            <option value={60}>60</option>
            <option value={120}>120</option>
          </select>
        </label>
      ) : null}
    </div>
  )
}

export default PlaybackControls

