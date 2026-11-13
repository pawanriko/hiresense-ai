// ScoreRing — the one visual form for a headline 0–100 score.
//
// WHAT: an SVG ring whose arc fills in proportion to `value`, with the
// number in the middle. Replaces the bare `.score` number on detail
// pages so a score reads at a glance, on a phone especially.
// WHERE: frontend/src/components/ScoreRing.jsx, styles in index.css
// (.score-ring). Used by Dashboard, ResumeDetail, AnalysisDetail and
// InterviewSession; later phases reuse it, they don't rebuild it.
// WHY mono: the arc uses var(--text) on a var(--stroke) track — no
// colour is introduced, so the ring works in both themes unchanged.
export default function ScoreRing({ value, label, size = 128 }) {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0))
  const stroke = 10
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (clamped / 100) * circumference

  return (
    <div
      className="score-ring"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label || 'Score'}: ${clamped} out of 100`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          className="score-ring-track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
        />
        <circle
          className="score-ring-arc"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="score-ring-center">
        <strong>{clamped}</strong>
        {label && <span>{label}</span>}
      </div>
    </div>
  )
}
