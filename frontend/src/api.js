// Tiny API client — the only place that knows how Django auth works.
//
// Auth is a Django session cookie (HttpOnly) plus a readable
// csrftoken cookie. Mutating requests send the token back as the
// X-CSRFToken header. Google/GitHub sign-in posts to django-allauth
// under /accounts/ and returns with the same session cookie set.

function getCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

async function ensureCsrf() {
  if (!getCsrfToken()) {
    await fetch('/api/auth/csrf/', { credentials: 'include' })
  }
  return getCsrfToken()
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (method !== 'GET' && method !== 'HEAD') {
    const token = await ensureCsrf()
    if (token) headers['X-CSRFToken'] = token
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
  const headers = {}
  const token = await ensureCsrf()
  if (token) headers['X-CSRFToken'] = token
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

async function startOAuth(provider) {
  const token = await ensureCsrf()
  const form = document.createElement('form')
  form.method = 'POST'
  form.action = `/accounts/${provider}/login/`
  const csrf = document.createElement('input')
  csrf.type = 'hidden'
  csrf.name = 'csrfmiddlewaretoken'
  csrf.value = token || ''
  form.appendChild(csrf)
  const next = document.createElement('input')
  next.type = 'hidden'
  next.name = 'next'
  next.value = '/'
  form.appendChild(next)
  document.body.appendChild(form)
  form.submit()
}

export const api = {
  csrf: () => request('/api/auth/csrf/'),
  me: () => request('/api/auth/me/'),
  login: (email, password) =>
    request('/api/auth/login/', { method: 'POST', body: { email, password } }),
  register: (name, email, password) =>
    request('/api/auth/register/', { method: 'POST', body: { name, email, password } }),
  logout: () => request('/api/auth/logout/', { method: 'POST' }),
  passwordReset: (email) =>
    request('/api/auth/password-reset/', { method: 'POST', body: { email } }),
  passwordResetConfirm: (uid, token, password) =>
    request('/api/auth/password-reset/confirm/', {
      method: 'POST',
      body: { uid, token, password },
    }),
  startOAuth,
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
