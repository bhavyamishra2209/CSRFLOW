import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import {
  LayoutDashboard,
  Upload,
  FileText,
  MessageSquare,
  Network,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  Shield,
} from 'lucide-react'

function Layout() {
  const { user, activeRole, roleConfig, signOut, isAdmin, isPM, isAuditor } = useAuth()
  const navigate = useNavigate()
  const [systemStatus, setSystemStatus] = useState('checking')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Health check
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.health()
        setSystemStatus('online')
      } catch (error) {
        setSystemStatus('offline')
      }
    }

    setSystemStatus('online')
    checkHealth()
  }, [])

  const handleSignOut = async () => {
    try {
      await signOut()
      navigate('/login')
    } catch (error) {
      console.error('Sign out error:', error)
    }
  }

  // Base navigation items with role permissions
  const baseNavigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['csr_head', 'project_manager', 'auditor'] },
    { name: 'Upload', href: '/upload', icon: Upload, roles: ['csr_head', 'project_manager'] },
    { name: 'Documents', href: '/documents', icon: FileText, roles: ['csr_head', 'project_manager', 'auditor'] },
    { name: 'Ask AI', href: '/ask-ai', icon: MessageSquare, roles: ['csr_head', 'project_manager', 'auditor'] },
    { name: 'Knowledge Graph', href: '/knowledge-graph', icon: Network, roles: ['csr_head', 'auditor'] },
    { name: 'Analytics', href: '/analytics', icon: BarChart3, roles: ['csr_head', 'project_manager', 'auditor'] },
    { name: 'Schemas', href: '/schemas', icon: Settings, roles: ['csr_head'] },
  ]

  // Filter navigation strictly by current logged-in role
  const navigation = baseNavigation.filter(item => item.roles.includes(activeRole))

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-gray-600 bg-opacity-75 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-30 w-64 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <Shield className="w-6 h-6 text-primary-600" />
              <h1 className="text-xl font-bold text-gray-800">CSRFlow AI</h1>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 rounded-md hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* FIXED LOGGED-IN ROLE BADGE (No dynamic switching after login) */}
          <div className="p-4 bg-gray-900 text-white border-b border-gray-800">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Logged In Role
              </span>
              <span className="px-2 py-0.5 text-[10px] font-extrabold bg-primary-600 text-white rounded-full">
                {roleConfig.badge}
              </span>
            </div>
            <p className="text-xs font-bold text-white truncate">{roleConfig.name}</p>
            <p className="text-[10px] text-gray-400 truncate mt-0.5">{roleConfig.email}</p>
          </div>

          {/* Navigation Items (Strictly Scoped) */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3 py-2.5 rounded-xl transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 font-bold shadow-sm'
                      : 'text-gray-700 hover:bg-gray-100 font-medium'
                  }`
                }
              >
                <item.icon className="w-5 h-5 text-primary-600" />
                <span className="text-sm">{item.name}</span>
              </NavLink>
            ))}
          </nav>

          {/* User Sign Out Section */}
          <div className="p-4 border-t border-gray-200 bg-gray-50/50 space-y-2">
            <button
              onClick={handleSignOut}
              className="w-full flex items-center justify-center space-x-2 px-3 py-2.5 text-xs font-bold text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-xl transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign Out / Switch Account</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="lg:pl-64">
        {/* Mobile Header */}
        <div className="lg:hidden flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <Menu className="w-6 h-6" />
          </button>
          <h1 className="text-lg font-bold text-gray-800">CSRFlow AI</h1>
          <span className="text-xs font-semibold px-2 py-1 bg-primary-100 text-primary-800 rounded">
            {roleConfig.badge}
          </span>
        </div>

        {/* Page Content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
