// Skeleton — placeholder shapes shown while a page's data loads.
//
// WHAT: grey pulsing blocks in the shape of what's coming, instead of
// a bare "Loading…" line. `Skeleton` is one block (give it a width via
// style); `SkeletonCard` mimics one .card; `SkeletonList` renders `n`
// cards for list pages. The shimmer is a slow opacity pulse on
// var(--panel-2) — the global reduced-motion rule already disables
// animation for users who ask for it.
// WHERE: frontend/src/components/Skeleton.jsx, styles in index.css
// (.skeleton). Every page's loading branch uses one of these.
export function Skeleton({ width = '100%', height = '1rem', style }) {
  return (
    <div
      className="skeleton"
      style={{ width, height, ...style }}
      aria-hidden="true"
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="card skeleton-card" aria-hidden="true">
      <Skeleton width="55%" height="1.1rem" />
      <Skeleton width="85%" />
      <Skeleton width="40%" />
    </div>
  )
}

export default function SkeletonList({ count = 3 }) {
  return (
    <div role="status" aria-label="Loading">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}
