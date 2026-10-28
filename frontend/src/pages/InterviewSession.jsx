import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'

function ScoreList({ scores }) {
  if (!scores) return null
  return (
    <p className="muted">
      Relevance {scores.relevance} · Depth {scores.depth} · Structure {scores.structure} ·{' '}
      Confidence {scores.confidence} · Conciseness {scores.conciseness}
    </p>
  )
}

export default function InterviewSession() {
  const { id } = useParams()
  const [session, setSession] = useState(null)
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.interviewDetail(id)
      .then(setSession)
      .catch((err) => setError(err.message))
  }, [id])

  async function handleAnswer(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const updated = await api.answerQuestion(id, answer)
      setSession(updated)
      setAnswer('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !session) return <p className="error">{error}</p>
  if (!session) return <p>Loading…</p>

  const answered = session.transcript.filter((item) => item.answer !== null)
  const lastAnswered = answered[answered.length - 1]
  const completed = session.status === 'completed'

  return (
    <section>
      <p><Link to="/interview">← Mock Interview</Link></p>
      <h1>
        {session.track} · {session.difficulty}
        {session.company && <span className="muted"> — {session.company}</span>}
      </h1>
      <p className="muted">
        Questions from: {session.question_source} ·{' '}
        {session.answered_count}/{session.total} answered
      </p>

      {completed ? (
        <>
          <p className="score">{session.overall_score}<span className="muted"> / 100 overall</span></p>
          <p className="muted">Feedback source: {session.report.feedback_source}</p>

          <h2>Scores by topic</h2>
          <ul className="list">
            {session.report.topic_scores.map((t) => (
              <li key={t.topic} className="card">
                {t.topic} — {t.score}/100
              </li>
            ))}
          </ul>

          <h2>Weakest areas</h2>
          {session.report.weakest_areas.length === 0 ? (
            <p className="muted">None — everything scored evenly.</p>
          ) : (
            <p>{session.report.weakest_areas.join(', ')}</p>
          )}

          {session.report.weakest_question && (
            <>
              <h2>Weakest question</h2>
              <div className="card">
                <p><strong>{session.report.weakest_question.question}</strong></p>
                <p className="muted">
                  Your answer scored {session.report.weakest_question.overall}/100
                </p>
                <p>{session.report.weakest_question.feedback}</p>
              </div>
            </>
          )}
        </>
      ) : (
        <>
          {lastAnswered && (
            <div className="card">
              <h2>Feedback on your last answer ({lastAnswered.overall}/100)</h2>
              <p>{lastAnswered.feedback}</p>
              <ScoreList scores={lastAnswered.scores} />
              <p className="muted">Feedback source: {lastAnswered.source}</p>
            </div>
          )}

          <h2>
            Question {session.answered_count + 1} of {session.total}
            <span className="muted"> · {session.current.topic}</span>
          </h2>
          <p><strong>{session.current.question}</strong></p>
          <form onSubmit={handleAnswer}>
            <label>
              Your answer
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={6}
                required
              />
            </label>
            <button type="submit" disabled={busy || answer.trim().length < 5}>
              {busy ? 'Scoring…' : 'Submit answer'}
            </button>
          </form>
          {error && <p className="error">{error}</p>}
        </>
      )}

      <h2>Transcript</h2>
      {answered.length === 0 ? (
        <p className="muted">No answers yet.</p>
      ) : (
        answered.map((item, index) => (
          <div className="card" key={index}>
            <p><strong>{item.question}</strong></p>
            <p>{item.answer}</p>
            <p className="muted">
              {item.overall}/100 · feedback: {item.source}
            </p>
            <p>{item.feedback}</p>
            <ScoreList scores={item.scores} />
          </div>
        ))
      )}
    </section>
  )
}
