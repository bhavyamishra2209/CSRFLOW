const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Get auth token from session
const getAuthToken = () => {
  const session = JSON.parse(localStorage.getItem('supabase.auth.token') || '{}')
  return session.access_token || 'csr-head-token'
}

// Base fetch with auth and error handling
async function fetchAPI(endpoint, options = {}) {
  const token = getAuthToken()
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  const config = {
    ...options,
    headers,
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config)
    
    // Handle 401 Unauthorized
    if (response.status === 401) {
      const errorData = await response.json().catch(() => ({}))
      const detailStr = typeof errorData.detail === 'object' ? JSON.stringify(errorData.detail) : (errorData.detail || errorData.message)
      throw new Error(detailStr || '401 Unauthorized: Access token missing or invalid')
    }

    // Handle 403 Forbidden
    if (response.status === 403) {
      const errorData = await response.json().catch(() => ({}))
      const detailMsg = errorData.detail?.message || errorData.detail || '403 Forbidden: Action restricted for your user role'
      throw new Error(detailMsg)
    }
    
    // Handle other errors
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const detailMsg = errorData.detail?.message || (typeof errorData.detail === 'object' ? JSON.stringify(errorData.detail) : errorData.detail) || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(detailMsg)
    }
    
    // Handle JSON responses
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      return await response.json()
    }
    
    return await response.text()
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error)
    throw error
  }
}

// API client methods
export const api = {
  health: async () => fetchAPI('/health'),
  
  // Document endpoints
  upload: async (file) => {
    const token = getAuthToken()
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail?.message || errorData.detail || 'Upload failed')
    }
    return await response.json()
  },
  
  documentsList: async () => fetchAPI('/documents/list'),
  getDocument: async (documentId) => fetchAPI(`/documents/${documentId}`),
  verifyDocument: async (documentId, payload = {}) => fetchAPI(`/documents/${documentId}/verify`, { method: 'POST', body: JSON.stringify(payload) }),
  query: async (queryText, useKg = false) => fetchAPI('/query', {
    method: 'POST',
    body: JSON.stringify({ query: queryText, use_kg: useKg }),
  }),
  kgVisualize: async () => fetchAPI('/kg/visualize'),
  userStats: async () => fetchAPI('/users/me/stats'),
  getSchema: async (docType) => fetchAPI(`/schemas/${encodeURIComponent(docType)}`),

  // -------------------------------------------------------------------------
  // 3-ROLE ENTERPRISE RBAC ENDPOINTS
  // -------------------------------------------------------------------------
  rbac: {
    // 1. CSR Head APIs
    head: {
      createProject: async (data) => fetchAPI('/rbac/head/projects', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
      getAllProjects: async () => fetchAPI('/rbac/head/projects'),
      assignTeam: async (caseId, assignments) => fetchAPI(`/rbac/head/projects/${caseId}/assign`, {
        method: 'PATCH',
        body: JSON.stringify(assignments),
      }),
      reopenProject: async (caseId) => fetchAPI(`/rbac/head/projects/${caseId}/reopen`, {
        method: 'PATCH',
      }),
      getUsers: async () => fetchAPI('/rbac/head/users'),
      createUser: async (userData) => fetchAPI('/rbac/head/users', {
        method: 'POST',
        body: JSON.stringify(userData),
      }),
      updateUserRole: async (userId, role) => fetchAPI(`/rbac/head/users/${userId}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      }),
      updateProject: async (caseId, details) => fetchAPI(`/rbac/head/projects/${caseId}/details`, {
        method: 'PATCH',
        body: JSON.stringify(details),
      }),
      closeProject: async (caseId) => fetchAPI(`/rbac/head/projects/${caseId}/close`, {
        method: 'PATCH',
      }),
      overrideProject: async (caseId, stage, comments) => fetchAPI(`/rbac/head/projects/${caseId}/override`, {
        method: 'POST',
        body: JSON.stringify({ target_stage: stage, comments }),
      }),
      resetAllData: async () => fetchAPI('/rbac/head/reset-all-data', {
        method: 'POST',
      }),
    },

    // 2. PM Execution APIs
    pm: {
      getAssignedProjects: async () => fetchAPI('/rbac/pm/projects'),
      updateProjectInfo: async (caseId, info) => fetchAPI(`/rbac/pm/projects/${caseId}/info`, {
        method: 'PATCH',
        body: JSON.stringify(info),
      }),
      uploadDocument: async (caseId, docData) => fetchAPI(`/rbac/pm/projects/${caseId}/documents`, {
        method: 'POST',
        body: JSON.stringify(docData),
      }),
      updateMilestone: async (caseId, milestoneData) => fetchAPI(`/rbac/pm/projects/${caseId}/milestones`, {
        method: 'POST',
        body: JSON.stringify(milestoneData),
      }),
      submitProject: async (caseId) => fetchAPI(`/rbac/pm/projects/${caseId}/submit`, {
        method: 'POST',
      }),
      updateStage: async (caseId, targetStage) => fetchAPI(`/rbac/pm/projects/${caseId}/stage`, {
        method: 'PATCH',
        body: JSON.stringify({ target_stage: targetStage }),
      }),
    },

    // 3. Approver / Auditor APIs
    auditor: {
      getAssignedProjects: async () => fetchAPI('/rbac/auditor/projects'),
      getAuditPack: async (caseId) => fetchAPI(`/rbac/auditor/projects/${caseId}/audit-pack`),
      verifyDocument: async (caseId, documentId, status, comments = '') => fetchAPI(`/rbac/auditor/projects/${caseId}/documents/${documentId}/verify`, {
        method: 'POST',
        body: JSON.stringify({ status, comments }),
      }),
      submitDecision: async (caseId, action, comments) => fetchAPI(`/rbac/auditor/projects/${caseId}/decision`, {
        method: 'POST',
        body: JSON.stringify({ action, comments }),
      }),
      markComplete: async (caseId) => fetchAPI(`/rbac/auditor/projects/${caseId}/complete`, {
        method: 'POST',
      }),
    },
  },
}

export default api
