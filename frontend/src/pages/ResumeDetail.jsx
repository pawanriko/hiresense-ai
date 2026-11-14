import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import ScoreRing from '../components/ScoreRing.jsx'
import ScoreBar from '../components/ScoreBar.jsx'
import SkeletonList from '../components/Skeleton.jsx'

export default function ResumeDetail() {
  const { id } = useParams()
  const [resume, setResume] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.resumeDetail(id)
      .then(setResume)
      .catch((err) => setError(err.message))
  }, [id])

  if (error) return <p className="error">{error}</p>
  if (!resume) return <SkeletonList count={3} />

  // What is lacking, first: every failed check across categories, with
  // the fix its detail string already describes.
  const failed = resume.breakdown.categories.flatMap((category) =>
    category.checks
      .filter((check) => !check.passed)
      .map((check) => ({ ...check, category: category.name })),
  )

  return (
    <section>
      <p><Link to="/resumes">← All resumes</Link></p>
      <h1>{resume.original_name}</h1>
      <div className="score-hero">
        <ScoreRing value={resume.ats_score} label="ATS" />
      </div>

      {failed.length > 0 ? (
        <div className="card">
          <h2>What to fix</h2>
          <ul className="list">
            {failed.map((check) => (
              <li key={`${check.category}-${check.name}`}>
                <span className="fail">✗</span>{' '}
                <strong>{check.name}</strong> — {check.detail}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="muted">Nothing missing — every check passed.</p>
      )}
      {resume.breakdown.categories.map((category) => (
        <div className="card" key={category.name}>
          <ScoreBar label={category.name} value={category.score} />
          <p className="muted">Weight {category.weight}</p>
          <ul className="list">
            {category.checks.map((check) => (
              <li key={check.name}>
                {check.passed
                  ? <span className="pass">✓</span>
                  : <span className="fail">✗</span>}{' '}
                <strong>{check.name}</strong> — {check.detail}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  )
}
