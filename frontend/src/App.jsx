import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api'
import Login from './pages/Login.jsx'
import Signup from './pages/Signup.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Resumes from './pages/Resumes.jsx'
import ResumeDetail from './pages/ResumeDetail.jsx'
import JdMatch from './pages/JdMatch.jsx'
import JdDetail from './pages/JdDetail.jsx'
import AnalysisDetail from './pages/AnalysisDetail.jsx'
import Interview from './pages/Interview.jsx'
import InterviewSession from './pages/InterviewSession.jsx'
import Applications from './pages/Applications.jsx'
import ApplicationDetail from './pages/ApplicationDetail.jsx'
import Tasks from './pages/Tasks.jsx'

// App owns the auth state: on load it asks Django who is signed in.
// Pages below only render when that question is answered, so a
// logged-out visitor never flashes the dashboard for a frame.
function Header({ user, onSignedOut, theme, onToggleTheme }) {
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
            <NavLink to="/resumes">Resumes</NavLink>
            <NavLink to="/jd-match">JD Match</NavLink>
            <NavLink to="/interview">Interview</NavLink>
            <NavLink to="/applications">Applications</NavLink>
            <NavLink to="/applications/tasks">Tasks</NavLink>
            <span className="muted">{user.username}</span>
            <button onClick={signOut}>Sign out</button>
          </>
        ) : (
          <NavLink to="/login">Sign in</NavLink>
        )}
        <button type="button" onClick={onToggleTheme} aria-label="Toggle dark / light mode">
          {theme === 'dark' ? '☀ Light' : '☾ Dark'}
        </button>
      </nav>
    </header>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  // Theme: index.html sets data-theme before first paint (from
  // localStorage); React adopts it and keeps the two in sync.
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || 'dark')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem('hiresense-theme', theme)
    } catch {
      // Private mode etc.: theme just won't persist.
    }
  }, [theme])

  // Cursor-tracking glow: feed the pointer position into CSS variables;
  // the .cursor-glow disc in index.css follows with a soft lag.
  useEffect(() => {
    let raf = 0
    function onMove(event) {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        document.documentElement.style.setProperty('--mx', `${event.clientX}px`)
        document.documentElement.style.setProperty('--my', `${event.clientY}px`)
      })
    }
    window.addEventListener('mousemove', onMove)
    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(raf)
    }
  }, [])

  useEffect(() => {
    api.me()
      .then((data) => setUser(data.authenticated ? { username: data.username } : null))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <main><p>Loading…</p></main>

  return (
    <BrowserRouter>
      <div className="cursor-glow" aria-hidden="true" />
      <Header
        user={user}
        onSignedOut={() => setUser(null)}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
      />
      <main>
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to="/" /> : <Login onSignedIn={setUser} />}
          />
          <Route
            path="/signup"
            element={user ? <Navigate to="/" /> : <Signup onSignedIn={setUser} />}
          />
          <Route
            path="/"
            element={user ? <Dashboard /> : <Navigate to="/login" />}
          />
          <Route
            path="/resumes"
            element={user ? <Resumes /> : <Navigate to="/login" />}
          />
          <Route
            path="/resumes/:id"
            element={user ? <ResumeDetail /> : <Navigate to="/login" />}
          />
          <Route
            path="/jd-match"
            element={user ? <JdMatch /> : <Navigate to="/login" />}
          />
          <Route
            path="/jd-match/:id"
            element={user ? <JdDetail /> : <Navigate to="/login" />}
          />
          <Route
            path="/jd-match/analyses/:id"
            element={user ? <AnalysisDetail /> : <Navigate to="/login" />}
          />
          <Route
            path="/interview"
            element={user ? <Interview /> : <Navigate to="/login" />}
          />
          <Route
            path="/interview/:id"
            element={user ? <InterviewSession /> : <Navigate to="/login" />}
          />
          <Route
            path="/applications"
            element={user ? <Applications /> : <Navigate to="/login" />}
          />
          <Route
            path="/applications/tasks"
            element={user ? <Tasks /> : <Navigate to="/login" />}
          />
          <Route
            path="/applications/:id"
            element={user ? <ApplicationDetail /> : <Navigate to="/login" />}
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
      <footer>
        <p>HireSense AI — candidate-side interview prep.</p>
        <p>Scoring is deterministic: AI never computes a score.</p>
        <p>
          Built by Pawan —{' '}
          <a href="https://github.com/pawanriko" target="_blank" rel="noreferrer">GitHub</a>
          {' · '}
          <a href="https://www.linkedin.com/in/pawanriko" target="_blank" rel="noreferrer">LinkedIn</a>
        </p>
      </footer>
    </BrowserRouter>
  )
}
