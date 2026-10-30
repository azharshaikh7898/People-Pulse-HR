// Thin wrapper around fetch: adds the JWT, parses JSON, turns failures into ApiError.
const BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const TOKEN_KEY = 'peoplepulse_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(message, status, fieldErrors = []) {
    super(message)
    this.status = status
    // [{field: 'email', message: '...'}] for 422 responses, so forms can show errors beside inputs
    this.fieldErrors = fieldErrors
  }
}

function toQuery(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.set(k, v)
  })
  const s = q.toString()
  return s ? `?${s}` : ''
}

async function request(path, { method = 'GET', body, form, params, auth = true } = {}) {
  const headers = {}
  const token = tokenStore.get()
  if (auth && token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = new URLSearchParams(form)
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  let res
  try {
    res = await fetch(`${BASE}${path}${toQuery(params)}`, { method, headers, body: payload })
  } catch {
    throw new ApiError('Cannot reach the server. Check your connection and that the backend is running.', 0)
  }

  if (res.status === 204) return null
  let data = null
  try { data = await res.json() } catch { /* non-JSON body */ }

  if (!res.ok) {
    if (res.status === 401 && auth && token) {
      tokenStore.clear()
      window.dispatchEvent(new Event('peoplepulse:unauthorized'))
    }
    const message = typeof data?.detail === 'string' ? data.detail : `Request failed (${res.status})`
    throw new ApiError(message, res.status, data?.errors || [])
  }
  return data
}

export const api = {
  login: (email, password) => request('/api/auth/login', { method: 'POST', form: { username: email, password }, auth: false }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  me: () => request('/api/auth/me'),
  changePassword: (body) => request('/api/auth/me/password', { method: 'PUT', body }),

  departments: () => request('/api/employees/departments'),
  listEmployees: (params) => request('/api/employees', { params }),
  getEmployee: (id) => request(`/api/employees/${id}`),
  createEmployee: (body) => request('/api/employees', { method: 'POST', body }),
  updateEmployee: (id, body) => request(`/api/employees/${id}`, { method: 'PUT', body }),
  deactivateEmployee: (id) => request(`/api/employees/${id}/deactivate`, { method: 'POST' }),
  activateEmployee: (id) => request(`/api/employees/${id}/activate`, { method: 'POST' }),

  listLeaves: (params) => request('/api/leaves', { params }),
  createLeave: (body) => request('/api/leaves', { method: 'POST', body }),
  reviewLeave: (id, body) => request(`/api/leaves/${id}/review`, { method: 'PATCH', body }),
  cancelLeave: (id) => request(`/api/leaves/${id}/cancel`, { method: 'POST' }),
  leaveBalance: (params) => request('/api/leaves/balance', { params }),

  onboardingTasks: (params) => request('/api/onboarding/tasks', { params }),
  updateTask: (id, status) => request(`/api/onboarding/tasks/${id}`, { method: 'PATCH', body: { status } }),
  onboardingProgress: () => request('/api/onboarding/progress'),

  dashboard: () => request('/api/analytics/dashboard'),
}
