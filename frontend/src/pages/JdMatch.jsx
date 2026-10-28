import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function JdMatch() {
  const [jds, setJds] = useState(null)
  const [analyses, setAnalyses] = useState(null)
  const [title, setTitle] = useState('')
  const [company, setCompany] = useState('')
  const [rawText, setRawText] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.jds().then((data) => setJds(data.jds)).catch((err) => setError(err.message))
    api.analyses().then((data) => setAnalyses(data.analyses)).catch((err) => setError(err.message))
  }, [])

  async function handleCreate(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const jd = await api.createJd(title, company, rawText)
      navigate(`/jd-match/${jd.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h1>JD Match</h1>
      <p className="muted">
        Paste a job description, edit the drafted criteria, then run it
        against one of your resumes. Scoring is deterministic — the
        criteria are the only thing AI ever touches, and only as a draft.
      </p>

      <form onSubmit={handleCreate}>
        <label>
          Role title
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          Company (optional)
          <input value={company} onChange={(e) => setCompany(e.target.value)} />
        </label>
        <label>
          Paste the full job description here…
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={7}
            required
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? 'Drafting criteria…' : 'Draft criteria'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}

      <h2>Saved job descriptions</h2>
      {jds === null ? (
        <p>Loading…</p>
      ) : jds.length === 0 ? (
        <p className="muted">Nothing here yet.</p>
      ) : (
        <ul className="list">
          {jds.map((jd) => (
            <li key={jd.id} className="card">
              <Link to={`/jd-match/${jd.id}`}>{jd.title}</Link>
              {jd.company && <span className="muted"> — {jd.company}</span>}
            </li>
          ))}
        </ul>
      )}

      <h2>Past analyses</h2>
      {analyses === null ? (
        <p>Loading…</p>
      ) : analyses.length === 0 ? (
        <p className="muted">Nothing here yet.</p>
      ) : (
        <ul className="list">
          {analyses.map((analysis) => (
            <li key={analysis.id} className="card">
              <Link to={`/jd-match/analyses/${analysis.id}`}>
                {analysis.jd_title} — {analysis.match_score}/100
              </Link>
              <span className="muted"> ({analysis.resume_name})</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
