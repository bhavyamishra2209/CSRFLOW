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
  Shield,
  Settings,
  LogOut,
  Menu,
  X,
} from 'lucide-react'

function Layout() {
  const { user, signOut, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [systemStatus, setSystemStatus] = useState('checking') // checking, online, offline, warming
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Check system health on mount and periodically
  useEffect(() => {
    let timeoutId
    let intervalId
    
    const checkHealth = async () => {
      try {
        const startTime = Date.now()
        await api.health()
        const responseTime = Date.now() - startTime
        
        // If response took > 5 seconds, system is warming up
        if (responseTime > 5000) {
          setSystemStatus('warming')
        } else {
          setSystemStatus('online')
        }
      } catch (error) {
        console.error('Health check failed:', error)
        setSystemStatus('offline')
      }
    }

    // Initial check with warming state for first 60 seconds
    setSystemStatus('warming')
    checkHealth()
    
    // Show warming state for at least 60 seconds on first load
    timeoutId = setTimeout(() => {
      if (systemStatus === 'warming') {
        checkHealth()
      }
    }, 60000)

    // Check every 30 seconds
    intervalId = setInterval(checkHealth, 30000)

    return () => {
      clearTimeout(timeoutId)
      clearInterval(intervalId)
    }
  }, [])

  const handleSignOut = async () => {
    try {
      await signOut()
      navigate('/login')
    } catch (error) {
      console.error('Sign out error:', error)
    }
  }

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Upload', href: '/upload', icon: Upload },
    { name: 'Documents', href: '/documents', icon: FileText },
    { name: 'Ask AI', href: '/ask-ai', icon: MessageSquare },
    { name: 'Knowledge Graph', href: '/knowledge-graph', icon: Network },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Security', href: '/security', icon: Shield },
  ]

  // Add schema management for admins
  if (isAdmin()) {
    navigation.push({ name: 'Schemas', href: '/schemas', icon: Settings })
  }

  const statusConfig = {
    checking: { color: 'bg-gray-400', text: 'Checking...', pulse: true },
    warming: { color: 'bg-yellow-400', text: 'Waking up server...', pulse: true },
    online: { color: 'bg-green-500', text: 'Online', pulse: false },
    offline: { color: 'bg-red-500', text: 'Offline', pulse: false },
  }

  const currentStatus = statusConfig[systemStatus]

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
          {/* Logo */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h1 className="text-xl font-bold text-gray-800">DocuMind AI</h1>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 rounded-md hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* System Status */}
          <div className="px-6 py-3 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <div className="relative">
                <div className={`w-2.5 h-2.5 rounded-full ${currentStatus.color}`} />
                {currentStatus.pulse && (
                  <div className={`absolute inset-0 w-2.5 h-2.5 rounded-full ${currentStatus.color} animate-ping`} />
                )}
              </div>
              <span className="text-sm text-gray-600">{currentStatus.text}</span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`
                }
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.name}</span>
              </NavLink>
            ))}
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-gray-200">
            <div className="flex items-center space-x-3 mb-3">
              <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white font-medium">
                {user?.email?.[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user?.email}
                </p>
                {isAdmin() && (
                  <p className="text-xs text-primary-600">Administrator</p>
                )}
              </div>
            </div>
            <button
              onClick={handleSignOut}
              className="w-full flex items-center justify-center space-x-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Mobile header */}
        <div className="lg:hidden flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <Menu className="w-6 h-6" />
          </button>
          <h1 className="text-lg font-bold text-gray-800">DocuMind AI</h1>
          <div className="w-10" /> {/* Spacer for centering */}
        </div>

        {/* Page content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
