import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import ScoreRing from '../components/ScoreRing.jsx'
import ScoreBar from '../components/ScoreBar.jsx'
import SkeletonList from '../components/Skeleton.jsx'
import { useToast } from '../components/toast-context.js'

export default function AnalysisDetail() {
  const { id } = useParams()
  const [analysis, setAnalysis] = useState(null)
  const [error, setError] = useState('')
  const [pushing, setPushing] = useState(false)
  const toast = useToast()

  useEffect(() => {
    api.analysisDetail(id)
      .then(setAnalysis)
      .catch((err) => setError(err.message))
  }, [id])

  async function handlePush() {
    setPushing(true)
    try {
      const result = await api.pushAnalysisGaps(id)
      toast.push(`${result.created} task(s) added to your checklist.`)
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setPushing(false)
    }
  }

  if (error) return <p className="error">{error}</p>
  if (!analysis) return <SkeletonList count={3} />

  return (
    <section>
      <p><Link to="/jd-match">← JD Match</Link></p>
      <h1>{analysis.jd_title}</h1>
      <p className="muted">Resume: {analysis.resume_name}</p>
      <div className="score-hero">
        <ScoreRing value={analysis.match_score} label="Match" />
      </div>

      <h2>Per-criterion results</h2>
      {analysis.criteria_results.map((result) => (
        <div className="card" key={result.name}>
          <ScoreBar label={result.name} value={result.score} />
          <p className="muted">
            {result.status} · weight {result.weight}
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

      <button onClick={handlePush} disabled={pushing}>
        {pushing ? 'Pushing…' : 'Push gaps to tasks'}
      </button>
      <p><Link to="/applications/tasks">Go to tasks →</Link></p>
    </section>
  )
}
