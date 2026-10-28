import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

const STATUSES = ['Applied', 'Interview', 'Offer', 'Rejected']

export default function Applications() {
  const [applications, setApplications] = useState(null)
  const [counts, setCounts] = useState({})
  const [jds, setJds] = useState([])
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [status, setStatus] = useState('Applied')
  const [notes, setNotes] = useState('')
  const [jdId, setJdId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function load() {
    api.applications()
      .then((data) => {
        setApplications(data.applications)
        setCounts(data.counts)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  useEffect(() => {
    api.jds().then((data) => setJds(data.jds)).catch(() => {})
  }, [])

  async function handleCreate(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.createApplication({
        company,
        role,
        status,
        notes,
        jd_id: jdId ? Number(jdId) : null,
      })
      setCompany('')
      setRole('')
      setStatus('Applied')
      setNotes('')
      setJdId('')
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function changeStatus(app, newStatus) {
    setError('')
    try {
      await api.updateApplication(app.id, { status: newStatus })
      load() // a status change moves the row to the top (updated_at)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section>
      <h1>Applications</h1>

      <form onSubmit={handleCreate}>
        <label>
          Company
          <input value={company} onChange={(e) => setCompany(e.target.value)} required />
        </label>
        <label>
          Role
          <input value={role} onChange={(e) => setRole(e.target.value)} required />
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Notes
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
        </label>
        <label>
          Linked job description (optional)
          <select value={jdId} onChange={(e) => setJdId(e.target.value)}>
            <option value="">No linked JD</option>
            {jds.map((jd) => (
              <option key={jd.id} value={jd.id}>{jd.title}</option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={busy}>
          {busy ? 'Saving…' : 'Add application'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}

      <div className="row">
        {STATUSES.map((s) => (
          <div className="card" key={s}>
            <strong>{counts[s] || 0}</strong>
            <p className="muted">{s}</p>
          </div>
        ))}
      </div>

      <p><Link to="/applications/tasks">Gap tasks →</Link></p>

      <h2>Tracker — recently updated first</h2>
      {applications === null ? (
        <p>Loading…</p>
      ) : applications.length === 0 ? (
        <p className="muted">Nothing here yet.</p>
      ) : (
        <ul className="list">
          {applications.map((app) => (
            <li key={app.id} className="card">
              <Link to={`/applications/${app.id}`}>
                {app.role} at {app.company}
              </Link>
              <span className="muted"> — {app.status}</span>
              {app.jd_title && <span className="muted"> · JD: {app.jd_title}</span>}
              {' '}
              <select
                value={app.status}
                onChange={(e) => changeStatus(app, e.target.value)}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
