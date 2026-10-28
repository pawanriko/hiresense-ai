import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api'
import Login from './pages/Login.jsx'
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
      </footer>
    </BrowserRouter>
  )
}
