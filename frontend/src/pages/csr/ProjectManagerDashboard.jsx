import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../api/client'
import {
  FolderOpen, CheckSquare, Clock, AlertTriangle,
  Upload, MessageSquare, ArrowRight, Flag,
} from 'lucide-react'

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

function MilestoneProgress({ milestones = [] }) {
  if (!milestones.length) return <span className="text-xs text-gray-400">No milestones</span>
  const done = milestones.filter((m) => m.status === 'completed').length
  const pct  = Math.round((done / milestones.length) * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-1.5 min-w-[60px]">
        <div
          className="bg-emerald-500 h-1.5 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 whitespace-nowrap">{done}/{milestones.length}</span>
    </div>
  )
}

export default function ProjectManagerDashboard() {
  const { user, profile } = useAuth()
  const [projects, setProjects] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  useEffect(() => { loadProjects() }, [])

  const loadProjects = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listProjects()
      setProjects(data)
    } catch (err) {
      setError(err.message || 'Failed to load projects.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
          <p className="text-sm text-gray-500">Loading your projects…</p>
        </div>
      </div>
    )
  }

  const active    = projects.filter((p) => ['in_progress', 'monitoring', 'approved'].includes(p.stage))
  const pending   = projects.filter((p) => ['draft', 'submitted'].includes(p.stage))
  const rejected  = projects.filter((p) => p.stage === 'rejected')

  const allMilestones = projects.flatMap((p) => (p.milestones || []).map((m) => ({ ...m, projectTitle: p.title, projectId: p.project_id })))
  const overdue = allMilestones.filter(
    (m) => m.status !== 'completed' && m.target_date && new Date(m.target_date) < new Date()
  )

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 17) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">

      {/* ── Header ── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {greeting()}, {profile?.full_name || user?.email?.split('@')[0]} 👋
        </h1>
        <p className="text-gray-500 text-sm mt-1">Project Manager · Your assigned projects</p>
      </div>

      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Assigned',  value: projects.length, icon: FolderOpen,   color: 'bg-indigo-500' },
          { label: 'Active',          value: active.length,   icon: CheckSquare,  color: 'bg-emerald-500' },
          { label: 'Awaiting Review', value: pending.length,  icon: Clock,        color: 'bg-amber-500' },
          { label: 'Overdue Tasks',   value: overdue.length,  icon: Flag,         color: overdue.length > 0 ? 'bg-red-500' : 'bg-gray-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-start gap-4">
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${color}`}>
              <Icon className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{value}</p>
              <p className="text-sm text-gray-500">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Overdue milestone alert ── */}
      {overdue.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-red-600" />
            <h3 className="text-sm font-semibold text-red-700">
              {overdue.length} overdue milestone{overdue.length > 1 ? 's' : ''}
            </h3>
          </div>
          <ul className="space-y-1.5">
            {overdue.slice(0, 4).map((m) => (
              <li key={m.milestone_id} className="text-xs text-red-600 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-red-400 rounded-full flex-shrink-0" />
                <Link to={`/csr/projects/${m.projectId}`} className="hover:underline font-medium">
                  {m.projectTitle}
                </Link>
                <span className="text-red-400">· {m.title} · due {m.target_date}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Rejected projects needing re-work ── */}
      {rejected.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4">
          <h3 className="text-sm font-semibold text-amber-700 mb-2">
            {rejected.length} project{rejected.length > 1 ? 's' : ''} need re-work after rejection
          </h3>
          <div className="flex flex-wrap gap-2">
            {rejected.map((p) => (
              <Link
                key={p.project_id}
                to={`/csr/projects/${p.project_id}`}
                className="text-xs bg-white border border-amber-200 text-amber-700 px-3 py-1.5 rounded-lg hover:bg-amber-50 transition-colors"
              >
                {p.title} →
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── Quick actions ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[
          { label: 'Upload Document',  to: '/upload',    icon: Upload,        color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
          { label: 'Ask AI Assistant', to: '/ask-ai',    icon: MessageSquare, color: 'bg-purple-50 text-purple-700 border-purple-200' },
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

      {/* ── Assigned projects list ── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Your Projects</h2>
          <span className="text-xs text-gray-400">{projects.length} assigned</span>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm">
            No projects assigned yet. Your CSR Head will assign you to projects.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-400 uppercase tracking-wide bg-gray-50">
                  <th className="text-left px-5 py-3 font-medium">Project</th>
                  <th className="text-left px-5 py-3 font-medium">Domain</th>
                  <th className="text-left px-5 py-3 font-medium">Stage</th>
                  <th className="text-left px-5 py-3 font-medium">Milestones</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {projects.map((p) => (
                  <tr key={p.project_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-gray-900 max-w-[180px] truncate">
                      {p.title}
                    </td>
                    <td className="px-5 py-3.5 capitalize text-gray-500">{p.domain}</td>
                    <td className="px-5 py-3.5">
                      <StageBadge stage={p.stage} label={p.stage_label} />
                    </td>
                    <td className="px-5 py-3.5 min-w-[140px]">
                      <MilestoneProgress milestones={p.milestones} />
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        to={`/csr/projects/${p.project_id}`}
                        className="text-indigo-600 hover:text-indigo-700 font-medium text-xs"
                      >
                        Open →
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
