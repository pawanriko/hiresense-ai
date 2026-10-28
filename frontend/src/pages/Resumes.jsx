import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function Resumes() {
  const [resumes, setResumes] = useState(null)
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [uploading, setUploading] = useState(false)

  function load() {
    api.resumes()
      .then((data) => setResumes(data.resumes))
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  async function handleUpload(event) {
    event.preventDefault()
    if (!file) return
    setError('')
    setNotice('')
    setUploading(true)
    try {
      const created = await api.uploadResume(file)
      setNotice(`Uploaded ${created.original_name} — ATS ${created.ats_score}/100`)
      setFile(null)
      event.target.reset()
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <section>
      <h1>Resumes</h1>

      <form onSubmit={handleUpload}>
        <label>
          Resume file (PDF or DOCX)
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={(e) => setFile(e.target.files[0] || null)}
            required
          />
        </label>
        <button type="submit" disabled={uploading || !file}>
          {uploading ? 'Scoring…' : 'Upload and score'}
        </button>
      </form>
      {notice && <p>{notice}</p>}
      {error && <p className="error">{error}</p>}

      <h2>Your resumes</h2>
      {resumes === null ? (
        <p>Loading…</p>
      ) : resumes.length === 0 ? (
        <p className="muted">Nothing here yet — upload your first resume above.</p>
      ) : (
        <ul className="list">
          {resumes.map((resume) => (
            <li key={resume.id} className="card">
              <Link to={`/resumes/${resume.id}`}>{resume.original_name}</Link>
              {' '}— ATS {resume.ats_score}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
