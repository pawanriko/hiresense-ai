import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Login({ onSignedIn }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [providers, setProviders] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.csrf()
      .then((data) => setProviders(data.providers || []))
      .catch(() => setProviders([]))
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const me = await api.login(email, password)
      if (!me.authenticated) throw new Error('Sign-in did not stick — try again')
      onSignedIn({ username: me.username })
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleOAuth(provider) {
    setError('')
    setBusy(true)
    try {
      await api.startOAuth(provider)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <section className="narrow">
      <h1>Welcome back</h1>
      <p className="tagline">Your sidekick for resumes, JD matches &amp; mock interviews.</p>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      {providers.includes('google') && (
        <p>
          <button type="button" onClick={() => handleOAuth('google')} disabled={busy}>
            Sign in with Google
          </button>
        </p>
      )}
      {providers.includes('github') && (
        <p>
          <button type="button" onClick={() => handleOAuth('github')} disabled={busy}>
            Sign in with GitHub
          </button>
        </p>
      )}
      <p className="muted">
        Forgot your password, or signed in with InsForge before?{' '}
        <Link to="/forgot-password">Set a new password</Link>
      </p>
      <p className="muted">
        New here? <Link to="/signup">Create an account</Link>
      </p>
      <p className="muted">
        Demo account: demo@hiresense.ai / demo1234
      </p>
    </section>
  )
}
