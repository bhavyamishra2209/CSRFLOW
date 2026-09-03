import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { createClient } from '@supabase/supabase-js'
import { api } from '../api/client'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

const supabase = createClient(supabaseUrl, supabaseAnonKey)

const AuthContext = createContext({})

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}

// Role constants — single source of truth for the entire frontend
export const ROLES = {
  CSR_HEAD: 'csr_head',
  PROJECT_MANAGER: 'project_manager',
  APPROVER: 'approver',
}

export const ROLE_LABELS = {
  csr_head: 'CSR Head',
  project_manager: 'Project Manager',
  approver: 'Approver / Auditor',
}

export const ROLE_DASHBOARD = {
  csr_head: '/csr/head',
  project_manager: '/csr/pm',
  approver: '/csr/approver',
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [session, setSession] = useState(null)
  const [csrRole, setCsrRole] = useState(null)   // 'csr_head' | 'project_manager' | 'approver'
  const [profile, setProfile] = useState(null)   // full user_profiles row
  const [loading, setLoading] = useState(true)
  const [roleLoading, setRoleLoading] = useState(false)

  // ── Fetch CSR role from backend after auth ───────────────────────────────
  const fetchProfile = useCallback(async (currentSession) => {
    if (!currentSession) {
      setCsrRole(null)
      setProfile(null)
      return
    }
    setRoleLoading(true)
    try {
      const data = await api.getMyProfile()
      setProfile(data)
      setCsrRole(data?.csr_role || null)
    } catch (err) {
      console.error('Failed to fetch CSR profile:', err)
      setCsrRole(null)
    } finally {
      setRoleLoading(false)
    }
  }, [])

  // ── Boot: restore session ─────────────────────────────────────────────────
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s)
      setUser(s?.user ?? null)
      if (s) {
        localStorage.setItem('supabase.auth.token', JSON.stringify({
          access_token: s.access_token,
          refresh_token: s.refresh_token,
        }))
        fetchProfile(s)
      }
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s)
      setUser(s?.user ?? null)
      if (s) {
        localStorage.setItem('supabase.auth.token', JSON.stringify({
          access_token: s.access_token,
          refresh_token: s.refresh_token,
        }))
        fetchProfile(s)
      } else {
        localStorage.removeItem('supabase.auth.token')
        setCsrRole(null)
        setProfile(null)
      }
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [fetchProfile])

  // ── Auth actions ──────────────────────────────────────────────────────────
  const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
    return data
  }

  const signUp = async (email, password, meta = {}) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: meta },
    })
    if (error) throw error
    return data
  }

  const signInWithMagicLink = async (email) => {
    const { data, error } = await supabase.auth.signInWithOtp({ email })
    if (error) throw error
    return data
  }

  const signOut = async () => {
    await supabase.auth.signOut()
    localStorage.removeItem('supabase.auth.token')
    setCsrRole(null)
    setProfile(null)
  }

  // ── Role helpers ──────────────────────────────────────────────────────────
  const isCSRHead = () => csrRole === ROLES.CSR_HEAD
  const isProjectManager = () => csrRole === ROLES.PROJECT_MANAGER
  const isApprover = () => csrRole === ROLES.APPROVER
  const hasRole = (...roles) => roles.includes(csrRole)

  /** Where to redirect this user after login */
  const getDashboardPath = () => ROLE_DASHBOARD[csrRole] || '/dashboard'

  /** Fallback isAdmin for legacy routes */
  const isAdmin = () => isCSRHead()

  const value = {
    // state
    user,
    session,
    profile,
    csrRole,
    loading: loading || roleLoading,
    roleLoading,
    // actions
    signIn,
    signUp,
    signInWithMagicLink,
    signOut,
    refreshProfile: () => fetchProfile(session),
    // role helpers
    isCSRHead,
    isProjectManager,
    isApprover,
    hasRole,
    getDashboardPath,
    isAdmin,  // legacy compat
    // constants
    ROLES,
    ROLE_LABELS,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthContext
