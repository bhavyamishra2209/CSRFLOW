import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth, ROLE_LABELS } from '../context/AuthContext'
import { Leaf, Mail, Lock, AlertCircle, CheckCircle } from 'lucide-react'

export default function Login() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { signIn, signInWithMagicLink, user, csrRole, getDashboardPath, loading } = useAuth()

  const [mode, setMode] = useState('password')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // ── Once role is known after login, redirect to role dashboard ───────────
  useEffect(() => {
    if (user && csrRole && !loading) {
      navigate(getDashboardPath(), { replace: true })
    }
  }, [user, csrRole, loading, navigate, getDashboardPath])

  // ── Session-expired banner ────────────────────────────────────────────────
  useEffect(() => {
    if (searchParams.get('expired') === 'true') {
      setError('Your session has expired. Please sign in again.')
    }
  }, [searchParams])

  const handlePasswordLogin = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setBusy(true)
    try {
      await signIn(email, password)
      // redirect happens via the useEffect above once csrRole loads
    } catch (err) {
      setError(err.message || 'Invalid email or password.')
    } finally {
      setBusy(false)
    }
  }

  const handleMagicLink = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setBusy(true)
    try {
      await signInWithMagicLink(email)
      setSuccess('Magic link sent! Check your inbox.')
    } catch (err) {
      setError(err.message || 'Failed to send magic link.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-teal-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        {/* ── Brand ── */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-600 rounded-2xl mb-4 shadow-lg">
            <Leaf className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">CSRFlow</h1>
          <p className="text-gray-500 mt-1 text-sm">CSR Project Lifecycle Management</p>
        </div>

        {/* ── Card ── */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8">

          {/* Alerts */}
          {error && (
            <div className="mb-5 flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-xl">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
          {success && (
            <div className="mb-5 flex items-start gap-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl">
              <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-emerald-700">{success}</p>
            </div>
          )}

          {/* Mode tabs */}
          <div className="flex rounded-xl bg-gray-100 p-1 mb-6">
            {['password', 'magic-link'].map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(''); setSuccess('') }}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${mode === m
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                  }`}
              >
                {m === 'password' ? 'Password' : 'Magic Link'}
              </button>
            ))}
          </div>

          {/* Password form */}
          {mode === 'password' && (
            <form onSubmit={handlePasswordLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    placeholder="you@company.com"
                    className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={busy}
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white font-semibold rounded-xl transition-colors text-sm mt-2"
              >
                {busy ? 'Signing in…' : 'Sign In'}
              </button>
            </form>
          )}

          {/* Magic-link form */}
          {mode === 'magic-link' && (
            <form onSubmit={handleMagicLink} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    placeholder="you@company.com"
                    className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  />
                </div>
                <p className="mt-1.5 text-xs text-gray-400">
                  We'll email you a one-click sign-in link — no password needed.
                </p>
              </div>
              <button
                type="submit"
                disabled={busy}
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white font-semibold rounded-xl transition-colors text-sm mt-2"
              >
                {busy ? 'Sending…' : 'Send Magic Link'}
              </button>
            </form>
          )}
        </div>

        {/* Role legend */}
        <div className="mt-6 bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Available roles
          </p>
          <div className="space-y-2">
            {[
              { role: 'csr_head', icon: '👩‍💼', desc: 'Creates & manages all CSR projects' },
              { role: 'project_manager', icon: '👨‍💻', desc: 'Executes assigned projects & uploads docs' },
              { role: 'approver', icon: '🧑‍⚖️', desc: 'Reviews proposals & approves stages' },
            ].map(({ role, icon, desc }) => (
              <div key={role} className="flex items-center gap-2.5">
                <span className="text-base">{icon}</span>
                <div>
                  <span className="text-xs font-semibold text-gray-700">
                    {ROLE_LABELS[role]}
                  </span>
                  <span className="text-xs text-gray-400 ml-1.5">— {desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-4">
          Secured with Supabase Auth + JWT · RBAC enforced server-side
        </p>
      </div>
    </div>
  )
}
