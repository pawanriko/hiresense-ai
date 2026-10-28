import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'

export default function AnalysisDetail() {
  const { id } = useParams()
  const [analysis, setAnalysis] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.analysisDetail(id)
      .then(setAnalysis)
      .catch((err) => setError(err.message))
  }, [id])

  if (error) return <p className="error">{error}</p>
  if (!analysis) return <p>Loading…</p>

  return (
    <section>
      <p><Link to="/jd-match">← JD Match</Link></p>
      <h1>{analysis.jd_title}</h1>
      <p className="muted">Resume: {analysis.resume_name}</p>
      <p className="score">{analysis.match_score}<span className="muted"> / 100 match</span></p>

      <h2>Per-criterion results</h2>
      {analysis.criteria_results.map((result) => (
        <div className="card" key={result.name}>
          <p>
            <strong>{result.name}</strong> — {result.score}/100 ({result.status})
            <span className="muted"> · weight {result.weight}</span>
          </p>
          {result.evidence ? (
            <p>“{result.evidence}” <small>({result.section})</small></p>
          ) : (
            <p className="muted">No evidence found in this resume.</p>
          )}
        </div>
      ))}

      <h2>Gaps and fix actions</h2>
      {analysis.gaps.length === 0 ? (
        <p className="muted">No gaps — every criterion came back strong or partial.</p>
      ) : (
        <ul className="list">
          {analysis.gaps.map((gap) => (
            <li key={gap.criterion} className="card">
              <strong>{gap.criterion} ({gap.current_status})</strong> — {gap.suggested_action}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
