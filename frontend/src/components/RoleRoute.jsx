import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * RoleRoute — wraps a page and only renders it if the logged-in user
 * has one of the allowed roles. Otherwise redirects to their own dashboard.
 *
 * Usage:
 *   <Route path="/csr/head" element={
 *     <RoleRoute allowed={['csr_head']}>
 *       <CSRHeadDashboard />
 *     </RoleRoute>
 *   } />
 */
export default function RoleRoute({ allowed, children }) {
  const { user, csrRole, loading, getDashboardPath } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600" />
          <p className="text-sm text-gray-500">Verifying access…</p>
        </div>
      </div>
    )
  }

  // Not logged in at all → go to login
  if (!user) return <Navigate to="/login" replace />

  // Logged in but role not loaded yet → wait
  if (csrRole === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600" />
          <p className="text-sm text-gray-500">Loading role…</p>
        </div>
      </div>
    )
  }

  // Wrong role → redirect to their own dashboard
  if (!allowed.includes(csrRole)) {
    return <Navigate to={getDashboardPath()} replace />
  }

  return children
}
