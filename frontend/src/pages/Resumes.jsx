import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import SkeletonList from '../components/Skeleton.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { useToast } from '../components/toast-context.js'

export default function Resumes() {
  const [resumes, setResumes] = useState(null)
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const toast = useToast()

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
    setUploading(true)
    try {
      const created = await api.uploadResume(file)
      toast.push(`Uploaded ${created.original_name} — ATS ${created.ats_score}/100`)
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
      {error && <p className="error">{error}</p>}

      <h2>Your resumes</h2>
      {resumes === null ? (
        <SkeletonList count={3} />
      ) : resumes.length === 0 ? (
        <EmptyState
          title="No resumes yet"
          hint="Upload your first resume above — PDF or DOCX."
        />
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
