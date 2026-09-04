import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, ROLE_CONFIG } from '../context/AuthContext'
import { Shield, Lock, AlertCircle, Briefcase, FileCheck, Mail, Key } from 'lucide-react'

function Login() {
  const navigate = useNavigate()
  const { loginWithRole } = useAuth()
  
  const [selectedRole, setSelectedRole] = useState('csr_head')
  const [email, setEmail] = useState('csrhead@csrflow.com')
  const [password, setPassword] = useState('password123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Role and Email Mismatch Validation Matrix
  const validateRoleEmailMatch = (role, emailStr) => {
    const cleanEmail = (emailStr || '').trim().toLowerCase()
    
    if (!cleanEmail) {
      return 'Account email address is required.'
    }

    if (role === 'csr_head') {
      if (cleanEmail.includes('pm') || cleanEmail.includes('manager') || cleanEmail.includes('auditor') || cleanEmail.includes('reviewer')) {
        return `Role & Email Mismatch: You selected '1. CSR Head (Admin)', but email '${cleanEmail}' belongs to a Project Manager or Auditor role.`
      }
    } else if (role === 'project_manager') {
      if (cleanEmail.includes('csrhead') || cleanEmail.includes('head') || cleanEmail.includes('auditor') || cleanEmail.includes('reviewer')) {
        return `Role & Email Mismatch: You selected '2. Project Manager (Execution)', but email '${cleanEmail}' belongs to CSR Head or Auditor role.`
      }
    } else if (role === 'auditor') {
      if (cleanEmail.includes('csrhead') || cleanEmail.includes('head') || cleanEmail.includes('pm') || cleanEmail.includes('manager')) {
        return `Role & Email Mismatch: You selected '3. Approver / Auditor (Reviewer)', but email '${cleanEmail}' belongs to CSR Head or Project Manager role.`
      }
    }

    return null
  }

  const handleRoleSelect = (roleKey) => {
    setSelectedRole(roleKey)
    setEmail(ROLE_CONFIG[roleKey].email)
    setError('')
  }

  const handleLogin = (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    // 1. Password validation
    if (!password || password.trim().length === 0) {
      setError('Password is required to sign in.')
      setLoading(false)
      return
    }

    // 2. Strict Role & Email Mismatch validation
    const mismatchError = validateRoleEmailMatch(selectedRole, email)
    if (mismatchError) {
      setError(mismatchError)
      setLoading(false)
      return
    }

    try {
      loginWithRole(selectedRole, email)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-950 via-gray-900 to-primary-900 flex items-center justify-center p-4">
      <div className="max-w-lg w-full">
        {/* Logo Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-2xl mb-3 shadow-xl shadow-primary-500/30">
            <Shield className="w-9 h-9 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">CSRFlow Enterprise</h1>
          <p className="text-primary-200 text-sm mt-1">Role-Based CSR Project Intelligence System</p>
        </div>

        {/* Login Form Card */}
        <div className="bg-white rounded-2xl p-8 shadow-2xl space-y-6">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Sign In to Your Workspace</h2>
            <p className="text-xs text-gray-500 mt-1">Role selection, account email, and password must match your credentials</p>
          </div>

          {/* Mismatch / Auth Alert Banner */}
          {error && (
            <div className="bg-red-50 border-2 border-red-200 text-red-800 p-4 rounded-xl text-xs space-y-1 shadow-sm">
              <div className="flex items-center space-x-2 font-bold text-red-900">
                <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                <span>Access Denied</span>
              </div>
              <p className="pl-6 font-medium leading-relaxed">{error}</p>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            {/* 1. ROLE SELECTION CARDS */}
            <div className="space-y-2.5">
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                1. Select Assigned Role
              </label>

              {/* CSR Head Card */}
              <div
                onClick={() => handleRoleSelect('csr_head')}
                className={`p-3.5 rounded-xl border-2 cursor-pointer transition-all flex items-center space-x-3 ${
                  selectedRole === 'csr_head'
                    ? 'border-primary-600 bg-primary-50/60 shadow-sm'
                    : 'border-gray-200 hover:border-gray-300 bg-gray-50/50'
                }`}
              >
                <div className={`p-2 rounded-lg ${selectedRole === 'csr_head' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                  <Shield className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-gray-900">1. CSR Head (Admin)</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-primary-600 text-white rounded-full">👑 Admin</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">Assigned Email: <code className="text-primary-700 font-bold">csrhead@csrflow.com</code></p>
                </div>
              </div>

              {/* Project Manager Card */}
              <div
                onClick={() => handleRoleSelect('project_manager')}
                className={`p-3.5 rounded-xl border-2 cursor-pointer transition-all flex items-center space-x-3 ${
                  selectedRole === 'project_manager'
                    ? 'border-primary-600 bg-primary-50/60 shadow-sm'
                    : 'border-gray-200 hover:border-gray-300 bg-gray-50/50'
                }`}
              >
                <div className={`p-2 rounded-lg ${selectedRole === 'project_manager' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                  <Briefcase className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-gray-900">2. Project Manager (Execution)</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-amber-600 text-white rounded-full">⚡ Execution</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">Assigned Email: <code className="text-amber-800 font-bold">pm@csrflow.com</code></p>
                </div>
              </div>

              {/* Approver / Auditor Card */}
              <div
                onClick={() => handleRoleSelect('auditor')}
                className={`p-3.5 rounded-xl border-2 cursor-pointer transition-all flex items-center space-x-3 ${
                  selectedRole === 'auditor'
                    ? 'border-primary-600 bg-primary-50/60 shadow-sm'
                    : 'border-gray-200 hover:border-gray-300 bg-gray-50/50'
                }`}
              >
                <div className={`p-2 rounded-lg ${selectedRole === 'auditor' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                  <FileCheck className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-gray-900">3. Approver / Auditor (Reviewer)</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-purple-600 text-white rounded-full">🔍 Reviewer</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">Assigned Email: <code className="text-purple-800 font-bold">auditor@csrflow.com</code></p>
                </div>
              </div>
            </div>

            {/* 2. EMAIL INPUT */}
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
                2. Account Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    setError('')
                  }}
                  placeholder="e.g. csrhead@csrflow.com"
                  className="w-full text-sm border rounded-xl pl-9 pr-3 py-2.5 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-primary-500 focus:outline-none font-medium"
                  required
                />
              </div>
            </div>

            {/* 3. PASSWORD INPUT */}
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
                3. Password
              </label>
              <div className="relative">
                <Key className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    setError('')
                  }}
                  placeholder="••••••••"
                  className="w-full text-sm border rounded-xl pl-9 pr-3 py-2.5 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-primary-500 focus:outline-none"
                  required
                />
              </div>
            </div>

            {/* SUBMIT BUTTON */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary-600 hover:bg-primary-700 text-white text-sm font-bold py-3 rounded-xl shadow-lg transition-all"
            >
              {loading ? 'Authenticating Role Credentials...' : `Sign In as ${ROLE_CONFIG[selectedRole].name}`}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default Login
