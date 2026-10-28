import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'

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
  if (!resume) return <p>Loading…</p>

  return (
    <section>
      <p><Link to="/resumes">← All resumes</Link></p>
      <h1>{resume.original_name}</h1>
      <p className="score">{resume.ats_score}<span className="muted"> / 100 ATS</span></p>

      {resume.breakdown.categories.map((category) => (
        <div className="card" key={category.name}>
          <h2>{category.name} — {category.score}/100 (weight {category.weight})</h2>
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
