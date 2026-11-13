// EmptyState — what an empty list says instead of one muted line.
//
// WHAT: a dashed-border panel with a title, one line of guidance, and
// an optional action (usually a <Link>). An empty list is a first-time
// user asking "what now?" — this answers it instead of trailing off.
// WHERE: frontend/src/components/EmptyState.jsx, styles in index.css
// (.empty-state). Pages pass their own title/hint/action; the panel
// stays the same everywhere so empty never looks like an error.
import { Link } from 'react-router-dom'

export default function EmptyState({ title, hint, actionTo, actionLabel }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {hint && <p className="muted">{hint}</p>}
      {actionTo && actionLabel && (
        <p>
          <Link to={actionTo}>{actionLabel} →</Link>
        </p>
      )}
    </div>
  )
}
