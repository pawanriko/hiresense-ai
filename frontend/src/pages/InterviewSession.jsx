import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import ScoreRing from '../components/ScoreRing.jsx'
import ScoreBar from '../components/ScoreBar.jsx'
import SkeletonList from '../components/Skeleton.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { useToast } from '../components/toast-context.js'

const DIMENSIONS = [
  ['relevance', 'Relevance'],
  ['depth', 'Depth'],
  ['structure', 'Structure'],
  ['confidence', 'Confidence'],
  ['conciseness', 'Conciseness'],
]

function ScoreList({ scores }) {
  if (!scores) return null
  return (
    <div>
      {DIMENSIONS.map(([key, label]) => (
        <ScoreBar key={key} label={label} value={scores[key]} />
      ))}
    </div>
  )
}

export default function InterviewSession() {
  const { id } = useParams()
  const [session, setSession] = useState(null)
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [pushing, setPushing] = useState(false)
  const toast = useToast()

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

  async function handlePush() {
    setPushing(true)
    try {
      const result = await api.pushInterviewAreas(id)
      toast.push(`${result.created} task(s) added to your checklist.`)
    } catch (err) {
      toast.push(err.message, 'error')
    } finally {
      setPushing(false)
    }
  }

  if (error && !session) return <p className="error">{error}</p>
  if (!session) return <SkeletonList count={3} />

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
          <div className="score-hero">
            <ScoreRing value={session.overall_score} label="Overall" />
          </div>
          <p className="muted">Feedback source: {session.report.feedback_source}</p>

          <h2>Scores by topic</h2>
          <div className="card">
            {session.report.topic_scores.map((t) => (
              <ScoreBar key={t.topic} label={t.topic} value={t.score} />
            ))}
          </div>

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

          <button onClick={handlePush} disabled={pushing}>
            {pushing ? 'Pushing…' : 'Push weakest areas to tasks'}
          </button>
          <p><Link to="/applications/tasks">Go to tasks →</Link></p>
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
        <EmptyState
          title="No answers yet"
          hint="Your answers and feedback will appear here as you go."
        />
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
