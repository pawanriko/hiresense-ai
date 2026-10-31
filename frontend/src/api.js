// Tiny API client — the only place that knows how Django auth works.
//
// HOW IT WORKS: Django uses session cookies + a CSRF token. Before the
// first POST we GET /api/auth/csrf/, which sets the `csrftoken` cookie
// (Django's CSRF cookie is readable by JS by design). Every later
// non-GET request sends that cookie's value back as the X-CSRFToken
// header, and `credentials: 'include'` makes the browser send the
// session cookie along. No tokens are stored anywhere in JS.
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
  return match ? decodeURIComponent(match[2]) : ''
}

let csrfReady = null
export function ensureCsrf() {
  if (!csrfReady) {
    csrfReady = fetch('/api/auth/csrf/', { credentials: 'include' }).then(() => {})
  }
  return csrfReady
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (method !== 'GET') {
    await ensureCsrf()
    headers['X-CSRFToken'] = getCookie('csrftoken')
  }
  const response = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || 'Request failed')
  }
  return data
}

async function requestFormData(path, formData) {
  // Multipart upload: the browser sets Content-Type (with boundary)
  // itself, so we must NOT set it — only the CSRF header goes on.
  await ensureCsrf()
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
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
  login: (username, password) =>
    request('/api/auth/login/', { method: 'POST', body: { username, password } }),
  register: (username, password, email) =>
    request('/api/auth/register/', {
      method: 'POST',
      body: { username, password, email },
    }),
  logout: () => request('/api/auth/logout/', { method: 'POST' }),
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
