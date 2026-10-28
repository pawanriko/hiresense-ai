import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'

const CATEGORIES = ['skill', 'tool', 'language', 'education', 'soft']

export default function JdDetail() {
  const { id } = useParams()
  const [jd, setJd] = useState(null)
  const [criteria, setCriteria] = useState([])
  const [resumes, setResumes] = useState([])
  const [selectedResume, setSelectedResume] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.jdDetail(id)
      .then((data) => {
        setJd(data)
        setCriteria(data.criteria)
      })
      .catch((err) => setError(err.message))
    // Only resumes with extracted text can be scored — the same
    // "parsed" filter the Django page's dropdown uses.
    api.resumes()
      .then((data) => setResumes(data.resumes.filter((r) => r.has_text)))
      .catch((err) => setError(err.message))
  }, [id])

  function updateRow(index, field, value) {
    setCriteria((rows) =>
      rows.map((row, i) => (i === index ? { ...row, [field]: value } : row)),
    )
  }

  async function handleSave() {
    setError('')
    setNotice('')
    setBusy(true)
    try {
      const saved = await api.saveCriteria(id, criteria)
      setJd(saved)
      setCriteria(saved.criteria)
      setNotice('Criteria saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleRedraft() {
    setError('')
    setNotice('')
    setBusy(true)
    try {
      const drafted = await api.redraftCriteria(id)
      setJd(drafted)
      setCriteria(drafted.criteria)
      setNotice('Fresh draft loaded — your edits were discarded.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleRun() {
    if (!selectedResume) return
    setError('')
    setNotice('')
    setBusy(true)
    try {
      const analysis = await api.runAnalysis(id, Number(selectedResume))
      navigate(`/jd-match/analyses/${analysis.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !jd) return <p className="error">{error}</p>
  if (!jd) return <p>Loading…</p>

  return (
    <section>
      <p><Link to="/jd-match">← JD Match</Link></p>
      <h1>{jd.title}{jd.company && <span className="muted"> — {jd.company}</span>}</h1>
      <p style={{ whiteSpace: 'pre-wrap' }}>{jd.raw_text}</p>

      <h2>Criteria — edit before scoring</h2>
      <p className="muted">
        Only saved criteria are scored. Save your edits first, then run the match.
        Total weight does not need to be exactly 100 — the engine uses a weighted average.
      </p>
      {criteria.map((row, index) => (
        <div className="card" key={index}>
          <label>
            Criterion
            <input
              value={row.name}
              onChange={(e) => updateRow(index, 'name', e.target.value)}
            />
          </label>
          <label>
            Category
            <select
              value={row.category}
              onChange={(e) => updateRow(index, 'category', e.target.value)}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
          <label>
            Weight
            <input
              type="number"
              min={0}
              max={100}
              value={row.weight}
              onChange={(e) => updateRow(index, 'weight', Number(e.target.value))}
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={row.required}
              onChange={(e) => updateRow(index, 'required', e.target.checked)}
            />
            Required
          </label>
          <button onClick={() => setCriteria((rows) => rows.filter((_, i) => i !== index))}>
            Remove
          </button>
        </div>
      ))}
      <button
        onClick={() => setCriteria((rows) => [
          ...rows,
          { name: '', category: 'skill', weight: 35, required: false },
        ])}
      >
        Add criterion
      </button>{' '}
      <button onClick={handleSave} disabled={busy}>
        {busy ? 'Saving…' : 'Save criteria'}
      </button>{' '}
      <button onClick={handleRedraft} disabled={busy}>
        Redraft
      </button>
      <p className="muted">Redraft replaces the criteria with a fresh draft and discards your edits.</p>
      {notice && <p>{notice}</p>}
      {error && <p className="error">{error}</p>}

      <h2>Run the match</h2>
      {resumes.length === 0 ? (
        <p className="muted">
          No parsed resumes yet — <Link to="/resumes">upload one first</Link>.
        </p>
      ) : (
        <>
          <label>
            Pick a resume…
            <select
              value={selectedResume}
              onChange={(e) => setSelectedResume(e.target.value)}
            >
              <option value="">Pick a resume…</option>
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>
                  {resume.original_name} (ATS {resume.ats_score})
                </option>
              ))}
            </select>
          </label>{' '}
          <button onClick={handleRun} disabled={busy || !selectedResume}>
            {busy ? 'Scoring…' : 'Run match'}
          </button>
        </>
      )}
    </section>
  )
}
