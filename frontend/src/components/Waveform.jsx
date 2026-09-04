export default function Waveform({ active }) {
  return (
    <div className={`waveform${active ? ' active' : ''}`} aria-hidden="true">
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} style={{ animationDelay: `${i * 0.1}s` }} />
      ))}
    </div>
  )
}