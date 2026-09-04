import { createContext, useContext, useEffect, useState } from 'react'

const AuthContext = createContext({})

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const ROLE_CONFIG = {
  csr_head: {
    id: 'csr_head',
    name: 'CSR Head (Admin)',
    token: 'csr-head-token',
    email: 'csrhead@csrflow.com',
    user_id: 'head_csr_001',
    badge: '👑 Admin',
    description: 'Full programme management, project creation & team assignments',
  },
  project_manager: {
    id: 'project_manager',
    name: 'Project Manager (Execution)',
    token: 'pm-token',
    email: 'pm@csrflow.com',
    user_id: 'pm_exec_101',
    badge: '⚡ Execution',
    description: 'Execution tracking, document uploads, milestones & proposal submission',
  },
  auditor: {
    id: 'auditor',
    name: 'Approver / Auditor (Reviewer)',
    token: 'auditor-token',
    email: 'auditor@csrflow.com',
    user_id: 'auditor_rev_201',
    badge: '🔍 Auditor',
    description: 'Independent review, statutory compliance inspection & decision approval',
  },
}

export const AuthProvider = ({ children }) => {
  const [activeRole, setActiveRole] = useState(() => {
    return localStorage.getItem('csr_active_role') || null
  })

  const [user, setUser] = useState(() => {
    const savedRole = localStorage.getItem('csr_active_role')
    if (!savedRole || !ROLE_CONFIG[savedRole]) return null
    const config = ROLE_CONFIG[savedRole]
    return {
      id: config.user_id,
      email: config.email,
      role: config.id,
    }
  })

  const currentRoleConfig = activeRole && ROLE_CONFIG[activeRole] ? ROLE_CONFIG[activeRole] : ROLE_CONFIG.csr_head

  // Login with selected role
  const loginWithRole = (selectedRole, customEmail) => {
    const config = ROLE_CONFIG[selectedRole] || ROLE_CONFIG.csr_head
    setActiveRole(selectedRole)
    localStorage.setItem('csr_active_role', selectedRole)
    localStorage.setItem('supabase.auth.token', JSON.stringify({
      access_token: config.token,
      refresh_token: 'dummy_refresh_token',
    }))

    setUser({
      id: config.user_id,
      email: customEmail || config.email,
      role: config.id,
    })
  }

  // Sign out clears session completely
  const signOut = async () => {
    localStorage.removeItem('supabase.auth.token')
    localStorage.removeItem('csr_active_role')
    setActiveRole(null)
    setUser(null)
  }

  const isAdmin = () => activeRole === 'csr_head'
  const isPM = () => activeRole === 'project_manager'
  const isAuditor = () => activeRole === 'auditor'

  const value = {
    user,
    activeRole: activeRole || 'csr_head',
    roleConfig: currentRoleConfig,
    loginWithRole,
    signOut,
    isAdmin,
    isPM,
    isAuditor,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export default AuthContext
