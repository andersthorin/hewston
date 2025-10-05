export type PlaybackControlsProps = {
  playing: boolean
  onPlay: () => void
  onPause: () => void
}

export function PlaybackControls({ playing, onPlay, onPause }: PlaybackControlsProps) {
  return (
    <div className="my-2 flex items-center gap-2">
      {playing ? (
        <button className="px-3 py-1 rounded bg-slate-800 text-white hover:bg-slate-700" onClick={onPause}>Pause</button>
      ) : (
        <button className="px-3 py-1 rounded bg-slate-800 text-white hover:bg-slate-700" onClick={onPlay}>Play</button>
      )}
    </div>
  )
}

export default PlaybackControls

