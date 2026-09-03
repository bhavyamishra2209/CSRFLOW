const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// ── Auth token ────────────────────────────────────────────────────────────

const getAuthToken = () => {
  try {
    const session = JSON.parse(localStorage.getItem('supabase.auth.token') || '{}')
    return session.access_token || null
  } catch {
    return null
  }
}

// ── Base fetch ────────────────────────────────────────────────────────────

async function fetchAPI(endpoint, options = {}) {
  const token = getAuthToken()

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (response.status === 401) {
      localStorage.removeItem('supabase.auth.token')
      window.location.href = '/login?expired=true'
      throw new Error('Session expired. Please log in again.')
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      // FastAPI wraps detail as object or string
      const msg =
        typeof err.detail === 'string'
          ? err.detail
          : err.detail?.detail || err.message || `HTTP ${response.status}`
      throw new Error(msg)
    }

    const ct = response.headers.get('content-type') || ''
    return ct.includes('application/json') ? response.json() : response.text()
  } catch (error) {
    console.error(`API [${endpoint}]:`, error)
    throw error
  }
}

// ── File upload (no Content-Type — browser sets multipart boundary) ────────

async function uploadFile(endpoint, file) {
  const token = getAuthToken()
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { Authorization: token ? `Bearer ${token}` : '' },
    body: formData,
  })

  if (response.status === 401) {
    localStorage.removeItem('supabase.auth.token')
    window.location.href = '/login?expired=true'
    throw new Error('Session expired.')
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || 'Upload failed')
  }
  return response.json()
}

// ── API surface ───────────────────────────────────────────────────────────

export const api = {
  // ── System ──────────────────────────────────────────────────────────────
  health: () => fetchAPI('/health'),

  // ── User profile ─────────────────────────────────────────────────────────
  /** Returns { id, email, full_name, organisation, csr_role, is_active, ... } */
  getMyProfile: () => fetchAPI('/users/me/profile'),

  updateMyProfile: (data) =>
    fetchAPI('/users/me/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /** csr_head only — list every user */
  listUsers: () => fetchAPI('/admin/users'),

  /** csr_head only — change a user's role */
  assignRole: (userId, csr_role) =>
    fetchAPI(`/admin/users/${userId}/role`, {
      method: 'PUT',
      body: JSON.stringify({ csr_role }),
    }),

  // ── CSR Projects ──────────────────────────────────────────────────────────
  /** csr_head — create a project */
  createProject: (data) =>
    fetchAPI('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** All roles — scoped list */
  listProjects: () => fetchAPI('/projects'),

  /** All roles — single project */
  getProject: (id) => fetchAPI(`/projects/${id}`),

  /** csr_head / pm — update title, domain, budget, description */
  updateProject: (id, data) =>
    fetchAPI(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /** csr_head — assign PM + approver */
  assignMembers: (id, data) =>
    fetchAPI(`/projects/${id}/assign`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /** Role-gated stage transition */
  transitionStage: (id, new_stage, comment = '') =>
    fetchAPI(`/projects/${id}/stage`, {
      method: 'POST',
      body: JSON.stringify({ new_stage, comment }),
    }),

  /** Add milestone */
  addMilestone: (projectId, data) =>
    fetchAPI(`/projects/${projectId}/milestones`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** Update milestone */
  updateMilestone: (projectId, milestoneId, data) =>
    fetchAPI(`/projects/${projectId}/milestones/${milestoneId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /** csr_head / approver — full stage history */
  getProjectHistory: (id) => fetchAPI(`/projects/${id}/history`),

  /** csr_head — aggregate stats */
  projectStats: () => fetchAPI('/projects/stats/summary'),

  // ── Legacy DocuMind AI routes ─────────────────────────────────────────────
  upload: (file) => uploadFile('/upload', file),
  documentsList: () => fetchAPI('/documents/list'),
  getDocument: (id) => fetchAPI(`/documents/${id}`),
  verifyDocument: (id) =>
    fetchAPI(`/documents/${id}/verify`, { method: 'POST' }),
  query: (queryText, useKg = false) =>
    fetchAPI('/query', {
      method: 'POST',
      body: JSON.stringify({ query: queryText, use_kg: useKg }),
    }),
  kgVisualize: () => fetchAPI('/kg/visualize'),
  userStats: () => fetchAPI('/users/me/stats'),
  getSchema: (docType) => fetchAPI(`/schemas/${encodeURIComponent(docType)}`),
  updateSchema: (docType, schemaData) =>
    fetchAPI(`/schemas/${encodeURIComponent(docType)}`, {
      method: 'PUT',
      body: JSON.stringify(schemaData),
    }),
}

export default api
