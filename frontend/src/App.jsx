import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import RoleRoute from './components/RoleRoute'

// Pages — auth
import Login from './pages/Login'

// Pages — CSR role dashboards
import CSRHeadDashboard from './pages/csr/CSRHeadDashboard'
import ProjectManagerDashboard from './pages/csr/ProjectManagerDashboard'
import ApproverDashboard from './pages/csr/ApproverDashboard'
import CreateProject from './pages/csr/CreateProject'
import ProjectDetail from './pages/csr/ProjectDetail'

// Pages — legacy DocuMind AI (all roles can access these)
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Documents from './pages/Documents'
import DocumentDetail from './pages/DocumentDetail'
import AskAI from './pages/AskAI'
import KnowledgeGraph from './pages/KnowledgeGraph'
import Analytics from './pages/Analytics'
import SchemaManagement from './pages/SchemaManagement'
import Security from './pages/Security'

// ── Loaders ───────────────────────────────────────────────────────────────

function FullPageSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center gap-3">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600" />
        <p className="text-sm text-gray-500">Loading…</p>
      </div>
    </div>
  )
}

// ── Guards ────────────────────────────────────────────────────────────────

/**
 * Requires the user to be logged in.
 * While auth is loading, shows a spinner.
 * Once loaded, unauthenticated users are sent to /login.
 */
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <FullPageSpinner />
  if (!user) return <Navigate to="/login" replace />
  return children
}

/**
 * The root index redirect.
 * Once the role is known, sends the user to their role-specific dashboard.
 * Falls back to /dashboard (legacy) if role is unknown.
 */
function RoleRedirect() {
  const { user, csrRole, loading, getDashboardPath } = useAuth()
  if (loading) return <FullPageSpinner />
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={getDashboardPath()} replace />
}

// ── App ───────────────────────────────────────────────────────────────────

function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />

      {/* Protected shell */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        {/* Root → role-specific dashboard */}
        <Route index element={<RoleRedirect />} />

        {/* ── CSR Head ── */}
        <Route
          path="csr/head"
          element={
            <RoleRoute allowed={['csr_head']}>
              <CSRHeadDashboard />
            </RoleRoute>
          }
        />

        {/* ── Project Manager ── */}
        <Route
          path="csr/pm"
          element={
            <RoleRoute allowed={['project_manager']}>
              <ProjectManagerDashboard />
            </RoleRoute>
          }
        />

        {/* ── Approver ── */}
        <Route
          path="csr/approver"
          element={
            <RoleRoute allowed={['approver']}>
              <ApproverDashboard />
            </RoleRoute>
          }
        />

        {/* ── Shared CSR pages (all roles) ── */}
        {/* NEW must come before :id so "new" isn't treated as a project ID */}
        <Route
          path="csr/projects/new"
          element={
            <RoleRoute allowed={['csr_head']}>
              <CreateProject />
            </RoleRoute>
          }
        />
        <Route path="csr/projects" element={<Documents />} />
        <Route path="csr/projects/:id" element={<ProjectDetail />} />

        {/* Team management — CSR Head only */}
        <Route
          path="csr/team"
          element={
            <RoleRoute allowed={['csr_head']}>
              {/* Reuse SchemaManagement slot for now; replace with TeamPage later */}
              <SchemaManagement />
            </RoleRoute>
          }
        />

        {/* ── Legacy DocuMind AI pages (accessible to all authenticated users) ── */}
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="upload" element={<Upload />} />
        <Route path="documents" element={<Documents />} />
        <Route path="documents/:id" element={<DocumentDetail />} />
        <Route path="ask-ai" element={<AskAI />} />
        <Route path="knowledge-graph" element={<KnowledgeGraph />} />
        <Route path="analytics" element={<Analytics />} />

        {/* Schemas — CSR Head only */}
        <Route
          path="schemas"
          element={
            <RoleRoute allowed={['csr_head']}>
              <SchemaManagement />
            </RoleRoute>
          }
        />

        {/* Security — CSR Head only */}
        <Route
          path="security"
          element={
            <RoleRoute allowed={['csr_head']}>
              <Security />
            </RoleRoute>
          }
        />

        {/* Fallback inside shell */}
        <Route path="*" element={<RoleRedirect />} />
      </Route>

      {/* Global fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AppRoutes />
      </Router>
    </AuthProvider>
  )
}
