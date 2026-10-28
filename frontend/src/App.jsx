import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'

// App owns the auth state: on load it asks Django who is signed in.
// Pages below only render when that question is answered, so a
// logged-out visitor never flashes the dashboard for a frame.
function Header({ user, onSignedOut }) {
  const navigate = useNavigate()
  async function signOut() {
    await api.logout()
    onSignedOut()
    navigate('/login')
  }
  return (
    <header>
      <strong>HireSense AI</strong>
      <nav>
        {user ? (
          <>
            <NavLink to="/">Dashboard</NavLink>
            <span className="muted">{user.username}</span>
            <button onClick={signOut}>Sign out</button>
          </>
        ) : (
          <NavLink to="/login">Sign in</NavLink>
        )}
      </nav>
    </header>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.me()
      .then((data) => setUser(data.authenticated ? { username: data.username } : null))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <main><p>Loading…</p></main>

  return (
    <BrowserRouter>
      <Header user={user} onSignedOut={() => setUser(null)} />
      <main>
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to="/" /> : <Login onSignedIn={setUser} />}
          />
          <Route
            path="/"
            element={user ? <Dashboard /> : <Navigate to="/login" />}
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
      <footer>
        <p>HireSense AI — candidate-side interview prep.</p>
        <p>Scoring is deterministic: AI never computes a score.</p>
      </footer>
    </BrowserRouter>
  )
}
