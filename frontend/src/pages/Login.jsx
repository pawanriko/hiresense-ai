import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import {
  INSFORGE_MODE,
  insforgeSignIn,
  insforgeSignInWithGoogle,
} from '../insforge'

export default function Login({ onSignedIn }) {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (INSFORGE_MODE) {
        // InsForge signs in with email. The SDK call only proves the
        // credential — me() is what creates/links the Django user
        // and returns the username the header shows.
        await insforgeSignIn(identifier, password)
        const me = await api.me()
        if (!me.authenticated) throw new Error('Sign-in did not stick — try again')
        onSignedIn({ username: me.username })
      } else {
        const data = await api.login(identifier, password)
        onSignedIn({ username: data.username })
      }
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleGoogle() {
    setError('')
    setBusy(true)
    try {
      // Redirects away to Google; the SDK finishes the flow when
      // Google sends the browser back to /login (see insforge.js).
      await insforgeSignInWithGoogle()
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
          {INSFORGE_MODE ? 'Email' : 'Username'}
          <input
            type={INSFORGE_MODE ? 'email' : 'text'}
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
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
      {INSFORGE_MODE && (
        <p>
          <button type="button" onClick={handleGoogle} disabled={busy}>
            Sign in with Google
          </button>
        </p>
      )}
      <p className="muted">
        New here? <Link to="/signup">Create an account</Link>
      </p>
      <p className="muted">
        {INSFORGE_MODE
          ? 'Demo account: demo@hiresense.ai / demo1234'
          : 'Demo account: demo / demo1234'}
      </p>
    </section>
  )
}
