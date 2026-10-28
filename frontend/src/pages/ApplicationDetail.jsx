import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'

const STATUSES = ['Applied', 'Interview', 'Offer', 'Rejected']

export default function ApplicationDetail() {
  const { id } = useParams()
  const [app, setApp] = useState(null)
  const [jds, setJds] = useState([])
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [status, setStatus] = useState('Applied')
  const [notes, setNotes] = useState('')
  const [jdId, setJdId] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.applicationDetail(id)
      .then((data) => {
        setApp(data)
        setCompany(data.company)
        setRole(data.role)
        setStatus(data.status)
        setNotes(data.notes)
        setJdId(data.jd_id ? String(data.jd_id) : '')
      })
      .catch((err) => setError(err.message))
    api.jds().then((data) => setJds(data.jds)).catch(() => {})
  }, [id])

  async function handleSave(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setBusy(true)
    try {
      const saved = await api.updateApplication(id, {
        company,
        role,
        status,
        notes,
        jd_id: jdId ? Number(jdId) : null,
      })
      setApp(saved)
      setNotice('Saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm('Delete this application?')) return
    setError('')
    try {
      await api.deleteApplication(id)
      navigate('/applications')
    } catch (err) {
      setError(err.message)
    }
  }

  if (error && !app) return <p className="error">{error}</p>
  if (!app) return <p>Loading…</p>

  return (
    <section>
      <p><Link to="/applications">← Applications</Link></p>
      <h1>{app.role} at {app.company}</h1>

      <form onSubmit={handleSave}>
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
          {busy ? 'Saving…' : 'Save'}
        </button>{' '}
        <button type="button" onClick={handleDelete}>
          Delete
        </button>
      </form>
      {notice && <p>{notice}</p>}
      {error && <p className="error">{error}</p>}
    </section>
  )
}
