// Tiny API client — the only place that knows how Django auth works.
//
// Every request carries the InsForge access token as Authorization:
// Bearer (see insforge.js — the token lives in memory, refreshed
// from an httpOnly cookie). Django verifies the token and exempts
// verified Bearer calls from CSRF (a token is not a cookie — see
// api/insforge_auth.py), so no CSRF header is sent. On a 401 the
// client refreshes the token once and retries once — access tokens
// live 15 minutes, so expiry mid-session is normal, not an error.
import {
  getAccessToken,
  insforgeSignOut,
  refreshInsforgeSession,
} from './insforge'

function bearerHeaders(headers) {
  const token = getAccessToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

async function request(path, { method = 'GET', body, _retried = false } = {}) {
  const headers = bearerHeaders({ 'Content-Type': 'application/json' })
  const response = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })
  if (response.status === 401 && !_retried) {
    const refreshed = await refreshInsforgeSession()
    if (refreshed) {
      return request(path, { method, body, _retried: true })
    }
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || 'Request failed')
  }
  return data
}

async function requestFormData(path, formData) {
  // Multipart upload: the browser sets Content-Type (with boundary)
  // itself, so we must NOT set it — only the Bearer header goes on.
  const headers = bearerHeaders({})
  const response = await fetch(path, {
    method: 'POST',
    headers,
    body: formData,
    credentials: 'include',
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || 'Request failed')
  }
  return data
}

export const api = {
  me: () => request('/api/auth/me/'),
  // Sign-in/up happen against InsForge directly (see insforge.js);
  // the pages call the SDK, then me(), and never touch Django auth.
  logout: () => insforgeSignOut(),
  dashboard: () => request('/api/dashboard/'),
  resumes: () => request('/api/resumes/'),
  resumeDetail: (id) => request(`/api/resumes/${id}/`),
  uploadResume: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return requestFormData('/api/resumes/upload/', formData)
  },
  jds: () => request('/api/jdmatch/jds/'),
  createJd: (title, company, raw_text) =>
    request('/api/jdmatch/jds/', { method: 'POST', body: { title, company, raw_text } }),
  jdDetail: (id) => request(`/api/jdmatch/jds/${id}/`),
  saveCriteria: (id, criteria) =>
    request(`/api/jdmatch/jds/${id}/criteria/`, { method: 'PUT', body: { criteria } }),
  redraftCriteria: (id) =>
    request(`/api/jdmatch/jds/${id}/redraft/`, { method: 'POST' }),
  analyses: () => request('/api/jdmatch/analyses/'),
  runAnalysis: (jd_id, resume_id) =>
    request('/api/jdmatch/analyses/', { method: 'POST', body: { jd_id, resume_id } }),
  analysisDetail: (id) => request(`/api/jdmatch/analyses/${id}/`),
  interviewSessions: () => request('/api/interview/sessions/'),
  startSession: (track, difficulty, company, jd_text) =>
    request('/api/interview/sessions/', { method: 'POST', body: { track, difficulty, company, jd_text } }),
  interviewDetail: (id) => request(`/api/interview/sessions/${id}/`),
  answerQuestion: (id, answer) =>
    request(`/api/interview/sessions/${id}/answer/`, { method: 'POST', body: { answer } }),
  applications: () => request('/api/applications/'),
  createApplication: (fields) =>
    request('/api/applications/', { method: 'POST', body: fields }),
  applicationDetail: (id) => request(`/api/applications/${id}/`),
  updateApplication: (id, fields) =>
    request(`/api/applications/${id}/`, { method: 'PUT', body: fields }),
  deleteApplication: (id) =>
    request(`/api/applications/${id}/`, { method: 'DELETE' }),
  tasks: (filter) => request(`/api/applications/tasks/?filter=${filter}`),
  createTask: (title, source_gap) =>
    request('/api/applications/tasks/', { method: 'POST', body: { title, source_gap } }),
  updateTask: (id, fields) =>
    request(`/api/applications/tasks/${id}/`, { method: 'PUT', body: fields }),
  pushAnalysisGaps: (id) =>
    request(`/api/applications/push/analysis/${id}/`, { method: 'POST' }),
  pushInterviewAreas: (id) =>
    request(`/api/applications/push/interview/${id}/`, { method: 'POST' }),
}
