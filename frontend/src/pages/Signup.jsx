import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { INSFORGE_MODE, insforgeSignUp } from '../insforge'

// Create an account. In InsForge mode the account lives in InsForge
// (email + password, verified by InsForge) and the first me() call
// creates the matching Django user; in session mode the server
// stores the password hashed (Django auth) and signs the new user in
// straight away. Either way a successful signup lands on the
// dashboard.
export default function Signup({ onSignedIn }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    setBusy(true)
    try {
      if (INSFORGE_MODE) {
        await insforgeSignUp(email, password, name)
        const me = await api.me()
        if (!me.authenticated) throw new Error('Sign-up did not stick — try signing in')
        onSignedIn({ username: me.username })
      } else {
        const data = await api.register(name, password, email)
        onSignedIn({ username: data.username })
      }
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="narrow">
      <h1>Create your account</h1>
      <p className="tagline">
        Your sidekick for resumes, JD matches &amp; mock interviews.
      </p>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          {INSFORGE_MODE ? 'Name (optional)' : 'Username'}
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete={INSFORGE_MODE ? 'nickname' : 'username'}
            required={!INSFORGE_MODE}
          />
        </label>
        <label>
          {INSFORGE_MODE ? 'Email' : 'Email (optional)'}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required={INSFORGE_MODE}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </label>
        <label>
          Confirm password
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            required
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="muted">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </section>
  )
}
