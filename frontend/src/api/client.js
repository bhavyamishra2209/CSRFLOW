const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://documind-ai-backend.onrender.com'

// Get auth token from session
const getAuthToken = () => {
  const session = JSON.parse(localStorage.getItem('supabase.auth.token') || '{}')
  return session.access_token || null
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
      // Clear session and redirect to login
      localStorage.removeItem('supabase.auth.token')
      window.location.href = '/login?expired=true'
      throw new Error('Session expired. Please log in again.')
    }
    
    // Handle other errors
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`)
    }
    
    // Handle empty responses
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
  // System health check
  health: async () => {
    return fetchAPI('/health')
  },
  
  // Document upload
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
    
    if (response.status === 401) {
      localStorage.removeItem('supabase.auth.token')
      window.location.href = '/login?expired=true'
      throw new Error('Session expired. Please log in again.')
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || errorData.message || 'Upload failed')
    }
    
    return await response.json()
  },
  
  // List documents
  documentsList: async () => {
    return fetchAPI('/documents/list')
  },
  
  // Get document by ID
  getDocument: async (documentId) => {
    return fetchAPI(`/documents/${documentId}`)
  },
  
  // Verify document
  verifyDocument: async (documentId) => {
    return fetchAPI(`/documents/${documentId}/verify`, {
      method: 'POST',
    })
  },
  
  // Query AI
  query: async (queryText, useKg = false) => {
    return fetchAPI('/query', {
      method: 'POST',
      body: JSON.stringify({
        query: queryText,
        use_kg: useKg,
      }),
    })
  },
  
  // Knowledge graph visualization
  kgVisualize: async () => {
    return fetchAPI('/kg/visualize')
  },
  
  // Get user statistics
  userStats: async () => {
    return fetchAPI('/users/me/stats')
  },
  
  // Get schema for document type
  getSchema: async (docType) => {
    return fetchAPI(`/schemas/${encodeURIComponent(docType)}`)
  },
  
  // Update schema for document type
  updateSchema: async (docType, schemaData) => {
    return fetchAPI(`/schemas/${encodeURIComponent(docType)}`, {
      method: 'PUT',
      body: JSON.stringify(schemaData),
    })
  },
  
  // Get current user info
  getCurrentUser: async () => {
    return fetchAPI('/users/me')
  },
}

export default api
