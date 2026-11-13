// StatusPill — a small status label that reads without colour.
//
// WHAT: the status word in a pill. Distinction comes from fill and
// border style only, never colour, so it stays mono in both themes:
//   Applied    — outline (waiting)
//   Interview  — filled, inverted (active, needs attention)
//   Offer      — filled + double border (the win state)
//   Rejected   — dashed border, muted (closed, recedes)
//   todo/doing/done and anything else fall back to the outline pill
//   with the given text, so new statuses never render unstyled.
// WHERE: frontend/src/components/StatusPill.jsx, styles in index.css
// (.pill). Used in Applications, ApplicationDetail, Interview lists
// and Tasks; Phase D's kanban reuses these same pills per column.
const TONES = {
  Applied: 'pill-outline',
  Interview: 'pill-filled',
  Offer: 'pill-offer',
  Rejected: 'pill-muted',
  todo: 'pill-outline',
  doing: 'pill-filled',
  done: 'pill-offer',
  completed: 'pill-offer',
  'in progress': 'pill-filled',
}

export default function StatusPill({ status }) {
  const tone = TONES[status] || 'pill-outline'
  return <span className={`pill ${tone}`}>{status}</span>
}
