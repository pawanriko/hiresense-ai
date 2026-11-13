// ScoreBar — one labelled 0–100 bar for a sub-score.
//
// WHAT: label on the left, number on the right, a hairline track with
// a filled portion underneath. Every sub-score in the app is 0–100
// (interview dimensions, resume categories, JD criteria, topic
// scores), so `max` defaults to 100 and rarely needs overriding.
// WHERE: frontend/src/components/ScoreBar.jsx, styles in index.css
// (.score-bar). Used wherever a page lists several scores side by
// side; the headline score on the same page uses ScoreRing instead.
export default function ScoreBar({ label, value, max = 100 }) {
  const clamped = Math.max(0, Math.min(max, Number(value) || 0))
  const percent = max > 0 ? (clamped / max) * 100 : 0

  return (
    <div className="score-bar">
      <div className="score-bar-head">
        <span>{label}</span>
        <strong>
          {clamped}
          <span className="muted"> / {max}</span>
        </strong>
      </div>
      <div
        className="score-bar-track"
        role="progressbar"
        aria-label={label}
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <div className="score-bar-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}
