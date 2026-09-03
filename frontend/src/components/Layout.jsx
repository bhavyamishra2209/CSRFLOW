import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth, ROLE_LABELS } from '../context/AuthContext'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import {
  LayoutDashboard, FolderOpen, Users, Upload, FileText,
  MessageSquare, Network, BarChart3, Settings, LogOut,
  Menu, X, Leaf, ClipboardCheck, ShieldCheck,
} from 'lucide-react'

// ── Role-specific nav configs ─────────────────────────────────────────────

const NAV_BY_ROLE = {
  csr_head: [
    { name: 'Dashboard', href: '/csr/head', icon: LayoutDashboard },
    { name: 'Projects', href: '/csr/projects', icon: FolderOpen },
    { name: 'Team', href: '/csr/team', icon: Users },
    { name: 'Documents', href: '/documents', icon: FileText },
    { name: 'Ask AI', href: '/ask-ai', icon: MessageSquare },
    { name: 'Knowledge Graph', href: '/knowledge-graph', icon: Network },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Schemas', href: '/schemas', icon: Settings },
  ],
  project_manager: [
    { name: 'Dashboard', href: '/csr/pm', icon: LayoutDashboard },
    { name: 'Projects', href: '/csr/projects', icon: FolderOpen },
    { name: 'Upload Doc', href: '/upload', icon: Upload },
    { name: 'Documents', href: '/documents', icon: FileText },
    { name: 'Ask AI', href: '/ask-ai', icon: MessageSquare },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  ],
  approver: [
    { name: 'Dashboard', href: '/csr/approver', icon: LayoutDashboard },
    { name: 'Review Queue', href: '/csr/projects', icon: ClipboardCheck },
    { name: 'Documents', href: '/documents', icon: FileText },
    { name: 'Audit Trail', href: '/analytics', icon: ShieldCheck },
    { name: 'Ask AI', href: '/ask-ai', icon: MessageSquare },
  ],
}

// Fallback for unauthenticated / unknown role
const NAV_DEFAULT = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Upload', href: '/upload', icon: Upload },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Ask AI', href: '/ask-ai', icon: MessageSquare },
]

// ── Role accent colours ───────────────────────────────────────────────────

const ROLE_ACCENT = {
  csr_head: { bg: 'bg-emerald-600', text: 'text-emerald-700', light: 'bg-emerald-50', ring: 'ring-emerald-500' },
  project_manager: { bg: 'bg-indigo-600', text: 'text-indigo-700', light: 'bg-indigo-50', ring: 'ring-indigo-500' },
  approver: { bg: 'bg-amber-600', text: 'text-amber-700', light: 'bg-amber-50', ring: 'ring-amber-500' },
}

export default function Layout() {
  const { user, csrRole, signOut, profile } = useAuth()
  const navigate = useNavigate()
  const [status, setStatus] = useState('warming')
  const [sidebarOpen, setSidebar] = useState(false)

  const accent = ROLE_ACCENT[csrRole] || ROLE_ACCENT.csr_head
  const nav = NAV_BY_ROLE[csrRole] || NAV_DEFAULT

  // ── Health polling ────────────────────────────────────────────────────────
  useEffect(() => {
    let interval
    const check = async () => {
      try {
        const t0 = Date.now()
        await api.health()
        setStatus(Date.now() - t0 > 5000 ? 'warming' : 'online')
      } catch {
        setStatus('offline')
      }
    }
    setStatus('warming')
    check()
    interval = setInterval(check, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleSignOut = async () => {
    try { await signOut() } catch { }
    navigate('/login')
  }

  const STATUS_DOT = {
    warming: { color: 'bg-yellow-400', label: 'Waking up…', pulse: true },
    online: { color: 'bg-green-500', label: 'Online', pulse: false },
    offline: { color: 'bg-red-500', label: 'Offline', pulse: false },
  }
  const dot = STATUS_DOT[status] || STATUS_DOT.warming

  const displayName = profile?.full_name || user?.email?.split('@')[0] || 'User'
  const roleLabel = ROLE_LABELS[csrRole] || 'User'

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-gray-900/50 z-20 lg:hidden"
          onClick={() => setSidebar(false)}
        />
      )}

      {/* ── Sidebar ────────────────────────────────────────────────────────── */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-64 bg-white border-r border-gray-100 flex flex-col
          transform transition-transform duration-300 lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        {/* Logo */}
        <div className={`flex items-center justify-between px-5 py-4 border-b border-gray-100 ${accent.bg}`}>
          <div className="flex items-center gap-2.5">
            <Leaf className="w-6 h-6 text-white" />
            <span className="text-lg font-bold text-white tracking-tight">CSRFlow</span>
          </div>
          <button
            onClick={() => setSidebar(false)}
            className="lg:hidden p-1 rounded text-white/80 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Server status */}
        <div className="flex items-center gap-2 px-5 py-2.5 border-b border-gray-100">
          <div className="relative flex-shrink-0">
            <div className={`w-2 h-2 rounded-full ${dot.color}`} />
            {dot.pulse && (
              <div className={`absolute inset-0 w-2 h-2 rounded-full ${dot.color} animate-ping`} />
            )}
          </div>
          <span className="text-xs text-gray-500">{dot.label}</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 overflow-y-auto space-y-0.5">
          {nav.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              onClick={() => setSidebar(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${isActive
                  ? `${accent.light} ${accent.text}`
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-gray-100">
          <div className="flex items-center gap-3 mb-3">
            <div className={`w-9 h-9 rounded-xl ${accent.bg} flex items-center justify-center text-white font-bold text-sm flex-shrink-0`}>
              {displayName[0].toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-gray-900 truncate">{displayName}</p>
              <p className={`text-xs font-medium ${accent.text}`}>{roleLabel}</p>
            </div>
          </div>
          <button
            onClick={handleSignOut}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────────────── */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        {/* Mobile topbar */}
        <header className="lg:hidden sticky top-0 z-10 flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 shadow-sm">
          <button onClick={() => setSidebar(true)} className="p-2 rounded-lg hover:bg-gray-100">
            <Menu className="w-5 h-5 text-gray-700" />
          </button>
          <div className="flex items-center gap-2">
            <Leaf className={`w-5 h-5 ${accent.text}`} />
            <span className="font-bold text-gray-900">CSRFlow</span>
          </div>
          <div className="w-9" />
        </header>

        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
