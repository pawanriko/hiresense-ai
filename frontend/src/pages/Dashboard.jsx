import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import ScoreRing from '../components/ScoreRing.jsx'
import SkeletonList from '../components/Skeleton.jsx'
import EmptyState from '../components/EmptyState.jsx'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.dashboard()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!data) return <SkeletonList count={3} />

  return (
    <section>
      <h1>Dashboard</h1>

      {data.latest ? (
        <div className="card score-hero">
          <ScoreRing value={data.latest.ats_score} label="ATS" />
          <div>
            <p className="muted">Latest resume</p>
            <p><Link to={`/resumes/${data.latest.id}`}>{data.latest.original_name}</Link></p>
          </div>
        </div>
      ) : (
        <EmptyState
          title="No resumes yet"
          hint="Upload your first resume and get an ATS score in seconds."
          actionTo="/resumes"
          actionLabel="Upload a resume"
        />
      )}

      <div className="row">
        <div className="card">
          <strong>{data.open_tasks}</strong>
          <p className="muted">Open tasks</p>
        </div>
        <div className="card">
          <strong>{data.done_tasks}</strong>
          <p className="muted">Done tasks</p>
        </div>
        {Object.entries(data.app_counts).map(([stage, count]) => (
          <div className="card" key={stage}>
            <strong>{count}</strong>
            <p className="muted">{stage}</p>
          </div>
        ))}
      </div>

      <h2>Resumes</h2>
      <p><Link to="/resumes">Upload a new resume →</Link></p>
      {data.resumes.length === 0 ? (
        <EmptyState
          title="Nothing here yet"
          hint="Your scored resumes will land here."
          actionTo="/resumes"
          actionLabel="Upload a resume"
        />
      ) : (
        <ul className="list">
          {data.resumes.map((resume) => (
            <li key={resume.id} className="card">
              {resume.original_name} — ATS {resume.ats_score}
            </li>
          ))}
        </ul>
      )}
      <p><Link to="/jd-match">Match a resume to a job →</Link></p>
      <p><Link to="/interview">Practise an interview →</Link></p>
      <p><Link to="/applications">Applications →</Link> · <Link to="/applications/tasks">Tasks →</Link></p>
    </section>
  )
}
