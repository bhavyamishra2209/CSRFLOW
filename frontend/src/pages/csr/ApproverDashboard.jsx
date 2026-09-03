import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../api/client'
import {
  ClipboardCheck, CheckCircle, XCircle, Clock,
  AlertTriangle, Eye, ShieldCheck, ArrowRight,
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

// Inline quick-approval inside the dashboard
function ApprovalActions({ project, onAction }) {
  const [comment, setComment] = useState('')
  const [busy, setBusy]       = useState(false)
  const [done, setDone]       = useState(false)

  // What stage to move to from current
  const nextApproved = project.stage === 'submitted'    ? 'under_review'
                     : project.stage === 'under_review' ? 'approved'
                     : project.stage === 'monitoring'   ? 'completed'
                     : null

  if (!nextApproved || done) return null

  const take = async (newStage) => {
    setBusy(true)
    try {
      await api.transitionStage(project.project_id, newStage, comment)
      setDone(true)
      onAction?.()
    } catch (err) {
      alert(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-3 space-y-2">
      <input
        type="text"
        placeholder="Add a comment (optional)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        className="w-full text-xs border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-amber-400"
      />
      <div className="flex gap-2">
        <button
          disabled={busy}
          onClick={() => take(nextApproved)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-xs font-semibold rounded-lg transition-colors"
        >
          <CheckCircle className="w-3.5 h-3.5" />
          {nextApproved === 'under_review' ? 'Begin Review' : nextApproved === 'approved' ? 'Approve' : 'Mark Complete'}
        </button>
        <button
          disabled={busy}
          onClick={() => take('rejected')}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-red-100 hover:bg-red-200 disabled:opacity-60 text-red-700 text-xs font-semibold rounded-lg transition-colors"
        >
          <XCircle className="w-3.5 h-3.5" />
          Reject
        </button>
      </div>
    </div>
  )
}

export default function ApproverDashboard() {
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
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-amber-600" />
          <p className="text-sm text-gray-500">Loading review queue…</p>
        </div>
      </div>
    )
  }

  const actionable = projects.filter((p) =>
    ['submitted', 'under_review', 'monitoring'].includes(p.stage)
  )
  const approved  = projects.filter((p) => p.stage === 'approved' || p.stage === 'completed' || p.stage === 'closed')
  const rejected  = projects.filter((p) => p.stage === 'rejected')

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
        <p className="text-gray-500 text-sm mt-1">Approver / Auditor · Review queue</p>
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
          { label: 'Total Assigned',  value: projects.length,  icon: ClipboardCheck, color: 'bg-amber-500' },
          { label: 'Needs Action',    value: actionable.length, icon: Clock,          color: actionable.length > 0 ? 'bg-red-500' : 'bg-gray-400' },
          { label: 'Approved',        value: approved.length,  icon: CheckCircle,    color: 'bg-emerald-500' },
          { label: 'Rejected',        value: rejected.length,  icon: XCircle,        color: 'bg-gray-400' },
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

      {/* ── Important notice ── */}
      <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-2xl text-sm text-amber-800">
        <ShieldCheck className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-600" />
        <span>
          <strong>Independence rule:</strong> You cannot approve or reject projects you created.
          The system enforces this automatically.
        </span>
      </div>

      {/* ── Action queue ── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-500" />
            Needs Your Action
            {actionable.length > 0 && (
              <span className="ml-1 px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full font-bold">
                {actionable.length}
              </span>
            )}
          </h2>
        </div>

        {actionable.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm">
            All caught up! No projects waiting for your review.
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {actionable.map((p) => (
              <div key={p.project_id} className="px-5 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900 text-sm truncate">{p.title}</h3>
                      <StageBadge stage={p.stage} label={p.stage_label} />
                    </div>
                    <p className="text-xs text-gray-400 mt-1 capitalize">
                      Domain: {p.domain}
                      {p.budget != null && ` · Budget: ₹${Number(p.budget).toLocaleString()}`}
                    </p>
                    <ApprovalActions project={p} onAction={loadProjects} />
                  </div>
                  <Link
                    to={`/csr/projects/${p.project_id}`}
                    className="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700 font-medium flex-shrink-0 mt-1"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Full review
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── All assigned projects ── */}
      {projects.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">All Assigned Projects</h2>
          </div>
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
                {projects.map((p) => (
                  <tr key={p.project_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-gray-900 max-w-[200px] truncate">{p.title}</td>
                    <td className="px-5 py-3.5 capitalize text-gray-500">{p.domain}</td>
                    <td className="px-5 py-3.5"><StageBadge stage={p.stage} label={p.stage_label} /></td>
                    <td className="px-5 py-3.5 text-right text-gray-600">
                      {p.budget != null ? `₹${Number(p.budget).toLocaleString()}` : '—'}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        to={`/csr/projects/${p.project_id}`}
                        className="text-amber-600 hover:text-amber-700 font-medium text-xs"
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
