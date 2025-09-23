export type PlaybackControlsProps = {
  playing: boolean
  speed: number
  onPlay: () => void
  onPause: () => void
  onSpeedChange: (s: number) => void
}

export function PlaybackControls({ playing, speed, onPlay, onPause, onSpeedChange }: PlaybackControlsProps) {
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', margin: '8px 0' }}>
      {playing ? (
        <button onClick={onPause}>Pause</button>
      ) : (
        <button onClick={onPlay}>Play</button>
      )}
      <label>
        Speed:
        <select value={speed} onChange={(e) => onSpeedChange(Number(e.target.value))}>
          <option value={30}>30</option>
          <option value={60}>60</option>
          <option value={120}>120</option>
        </select>
      </label>
    </div>
  )
}

export default PlaybackControls

