import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import StatusPill from '../components/StatusPill.jsx'
import SkeletonList from '../components/Skeleton.jsx'
import EmptyState from '../components/EmptyState.jsx'

const TRACKS = ['HR', 'Technical', 'DSA', 'Frontend']
const DIFFICULTIES = ['easy', 'medium', 'hard']

export default function Interview() {
  const [sessions, setSessions] = useState(null)
  const [track, setTrack] = useState('HR')
  const [difficulty, setDifficulty] = useState('medium')
  const [company, setCompany] = useState('')
  const [jdText, setJdText] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.interviewSessions()
      .then((data) => setSessions(data.sessions))
      .catch((err) => setError(err.message))
  }, [])

  async function handleStart(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const session = await api.startSession(track, difficulty, company, jdText)
      navigate(`/interview/${session.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h1>Mock Interview</h1>
      <p className="muted">
        Five questions, one at a time, scored on relevance, depth,
        structure, confidence, and conciseness. Questions come from the
        bank unless an AI provider is configured — and then only the
        questions and feedback wording come from AI, never the rubric.
      </p>

      <form onSubmit={handleStart}>
        <label>
          Track
          <select value={track} onChange={(e) => setTrack(e.target.value)}>
            {TRACKS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>
        <label>
          Difficulty
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </label>
        <label>
          Company (optional — grounds AI questions)
          <input value={company} onChange={(e) => setCompany(e.target.value)} />
        </label>
        <label>
          Job description (optional — grounds AI questions)
          <textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            rows={5}
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? 'Starting…' : 'Start session'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}

      <h2>Past sessions</h2>
      {sessions === null ? (
        <SkeletonList count={3} />
      ) : sessions.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          hint="Start your first mock interview above — five questions, one at a time."
        />
      ) : (
        <ul className="list">
          {sessions.map((session) => (
            <li key={session.id} className="card">
              <Link to={`/interview/${session.id}`}>
                {session.track} · {session.difficulty}
              </Link>{' '}
              <StatusPill status={session.status === 'completed' ? 'completed' : 'in progress'} />
              <span className="muted">
                {' '}{session.status === 'completed'
                  ? `${session.overall_score}/100`
                  : `${session.answered_count}/${session.total} answered`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
