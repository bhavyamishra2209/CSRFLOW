import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../api/client'
import {
  FolderOpen, Users, DollarSign, CheckCircle, Clock,
  AlertTriangle, PlusCircle, ArrowRight, BarChart2,
  TrendingUp, Activity,
} from 'lucide-react'

// ── Small reusable stat card ──────────────────────────────────────────────
function StatCard({ label, value, icon: Icon, color, sub }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-start gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value ?? '—'}</p>
        <p className="text-sm text-gray-500">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

// ── Stage badge ───────────────────────────────────────────────────────────
const STAGE_COLOR = {
  draft:        'bg-gray-100 text-gray-600',
  submitted:    'bg-blue-100 text-blue-700',
  under_review: 'bg-yellow-100 text-yellow-700',
  approved:     'bg-emerald-100 text-emerald-700',
  rejected:     'bg-red-100 text-red-700',
  in_progress:  'bg-indigo-100 text-indigo-700',
  monitoring:   'bg-purple-100 text-purple-700',
  completed:    'bg-teal-100 text-teal-700',
  closed:       'bg-gray-200 text-gray-500',
}

function StageBadge({ stage, label }) {
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${STAGE_COLOR[stage] || 'bg-gray-100 text-gray-600'}`}>
      {label || stage}
    </span>
  )
}

export default function CSRHeadDashboard() {
  const { user, profile } = useAuth()
  const [projects, setProjects] = useState([])
  const [stats, setStats]       = useState(null)
  const [users, setUsers]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    setLoading(true)
    setError('')
    try {
      const [projList, summary, userList] = await Promise.all([
        api.listProjects(),
        api.projectStats(),
        api.listUsers(),
      ])
      setProjects(projList)
      setStats(summary)
      setUsers(userList)
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data.')
    } finally {
      setLoading(false)
    }
  }

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 17) return 'Good afternoon'
    return 'Good evening'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600" />
          <p className="text-sm text-gray-500">Loading dashboard…</p>
        </div>
      </div>
    )
  }

  const recentProjects = [...projects]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5)

  const pendingApproval = projects.filter(
    (p) => p.stage === 'submitted' || p.stage === 'under_review'
  ).length

  const pmCount       = users.filter((u) => u.csr_role === 'project_manager').length
  const approverCount = users.filter((u) => u.csr_role === 'approver').length

  return (
    <div className="max-w-7xl mx-auto space-y-8">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {greeting()}, {profile?.full_name || user?.email?.split('@')[0]} 👋
          </h1>
          <p className="text-gray-500 text-sm mt-1">CSR Head · Full programme overview</p>
        </div>
        <Link
          to="/csr/projects/new"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm"
        >
          <PlusCircle className="w-4 h-4" />
          New Project
        </Link>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Projects"
          value={stats?.total_projects ?? projects.length}
          icon={FolderOpen}
          color="bg-emerald-500"
        />
        <StatCard
          label="Active Projects"
          value={stats?.active_projects ?? 0}
          icon={Activity}
          color="bg-indigo-500"
          sub="in_progress + monitoring"
        />
        <StatCard
          label="Pending Approval"
          value={pendingApproval}
          icon={Clock}
          color="bg-amber-500"
          sub="awaiting review"
        />
        <StatCard
          label="Total Budget"
          value={stats?.total_budget != null
            ? `₹${(stats.total_budget / 100000).toFixed(1)}L`
            : '—'}
          icon={DollarSign}
          color="bg-teal-500"
        />
      </div>

      {/* ── Team overview ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Team Size</p>
          <p className="text-3xl font-bold text-gray-900">{users.length}</p>
          <p className="text-xs text-gray-500 mt-1">Total users</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Project Managers</p>
          <p className="text-3xl font-bold text-indigo-600">{pmCount}</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Approvers</p>
          <p className="text-3xl font-bold text-amber-600">{approverCount}</p>
        </div>
      </div>

      {/* ── Projects by stage ── */}
      {stats?.by_stage && Object.keys(stats.by_stage).length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-emerald-600" />
            Projects by Stage
          </h2>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.by_stage).map(([stage, count]) => (
              <div
                key={stage}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-xl ${STAGE_COLOR[stage] || 'bg-gray-100 text-gray-600'}`}
              >
                <span className="font-bold text-lg">{count}</span>
                <span className="text-xs capitalize">{stage.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Quick actions ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Create Project',    to: '/csr/projects/new',  icon: PlusCircle,  color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
          { label: 'Manage Team',       to: '/csr/team',          icon: Users,       color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
          { label: 'View All Projects', to: '/csr/projects',      icon: TrendingUp,  color: 'bg-amber-50 text-amber-700 border-amber-200' },
        ].map(({ label, to, icon: Icon, color }) => (
          <Link
            key={label}
            to={to}
            className={`flex items-center justify-between p-4 rounded-2xl border font-medium text-sm transition-opacity hover:opacity-80 ${color}`}
          >
            <span className="flex items-center gap-2">
              <Icon className="w-4 h-4" />
              {label}
            </span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        ))}
      </div>

      {/* ── Recent projects table ── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700">Recent Projects</h2>
          <Link to="/csr/projects" className="text-xs text-emerald-600 hover:text-emerald-700 font-medium">
            View all →
          </Link>
        </div>
        {recentProjects.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm">
            No projects yet.{' '}
            <Link to="/csr/projects/new" className="text-emerald-600 underline">
              Create the first one
            </Link>.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-400 uppercase tracking-wide bg-gray-50">
                  <th className="text-left px-5 py-3 font-medium">Project</th>
                  <th className="text-left px-5 py-3 font-medium">Domain</th>
                  <th className="text-left px-5 py-3 font-medium">Stage</th>
                  <th className="text-right px-5 py-3 font-medium">Budget</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recentProjects.map((p) => (
                  <tr key={p.project_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-gray-900 max-w-[200px] truncate">
                      {p.title}
                    </td>
                    <td className="px-5 py-3.5 capitalize text-gray-500">{p.domain}</td>
                    <td className="px-5 py-3.5">
                      <StageBadge stage={p.stage} label={p.stage_label} />
                    </td>
                    <td className="px-5 py-3.5 text-right text-gray-600">
                      {p.budget != null ? `₹${Number(p.budget).toLocaleString()}` : '—'}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        to={`/csr/projects/${p.project_id}`}
                        className="text-emerald-600 hover:text-emerald-700 font-medium text-xs"
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
