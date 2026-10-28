import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.dashboard()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!data) return <p>Loading…</p>

  return (
    <section>
      <h1>Dashboard</h1>

      {data.latest ? (
        <div className="card">
          <p className="muted">Latest resume: {data.latest.original_name}</p>
          <p className="score">{data.latest.ats_score}<span className="muted"> / 100 ATS</span></p>
        </div>
      ) : (
        <div className="card"><p>No resumes yet.</p></div>
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
      {data.resumes.length === 0 ? (
        <p className="muted">Nothing here yet.</p>
      ) : (
        <ul className="list">
          {data.resumes.map((resume) => (
            <li key={resume.id} className="card">
              {resume.original_name} — ATS {resume.ats_score}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
