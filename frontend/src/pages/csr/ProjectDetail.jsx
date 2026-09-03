import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { api } from '../../api/client'
import {
  ArrowLeft, CheckCircle, XCircle, Clock, AlertTriangle,
  DollarSign, CalendarDays, Users, Flag, ChevronRight,
  PlusCircle, Edit3, ShieldCheck, History, CheckSquare,
} from 'lucide-react'

// ── Helpers ───────────────────────────────────────────────────────────────

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

const MILESTONE_STATUS_COLOR = {
  pending:     'bg-gray-100 text-gray-600',
  in_progress: 'bg-blue-100 text-blue-700',
  completed:   'bg-emerald-100 text-emerald-700',
  overdue:     'bg-red-100 text-red-700',
}

function StageBadge({ stage, label }) {
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${STAGE_COLOR[stage] || 'bg-gray-100 text-gray-600'}`}>
      {label || stage}
    </span>
  )
}

// Which stage transitions are available per role from a given stage
const NEXT_STAGES = {
  csr_head: {
    draft:       [],
    submitted:   [],
    approved:    [{ label: 'Start Project', stage: 'in_progress' }],
    in_progress: [{ label: 'Move to Monitoring', stage: 'monitoring' }],
    completed:   [{ label: 'Close Project', stage: 'closed' }],
    rejected:    [],
  },
  project_manager: {
    draft:       [{ label: 'Submit for Review', stage: 'submitted' }],
    rejected:    [{ label: 'Re-submit as Draft', stage: 'draft' }],
    approved:    [{ label: 'Start Project', stage: 'in_progress' }],
    in_progress: [{ label: 'Move to Monitoring', stage: 'monitoring' }],
  },
  approver: {
    submitted:    [
      { label: 'Begin Review',  stage: 'under_review' },
      { label: 'Reject',        stage: 'rejected', danger: true },
    ],
    under_review: [
      { label: 'Approve',       stage: 'approved' },
      { label: 'Reject',        stage: 'rejected', danger: true },
    ],
    monitoring:   [
      { label: 'Mark Complete', stage: 'completed' },
    ],
  },
}

// ── Stage Transition Panel ────────────────────────────────────────────────

function StageActions({ project, csrRole, onTransition }) {
  const [comment, setComment] = useState('')
  const [busy, setBusy]       = useState(false)
  const [error, setError]     = useState('')

  const actions = NEXT_STAGES[csrRole]?.[project.stage] || []
  if (!actions.length) return null

  // Approver self-approval guard (frontend hint — backend enforces too)
  const isSelfCreated = project.created_by === project.assigned_approver
  if (csrRole === 'approver' && isSelfCreated) {
    return (
      <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-700">
        <ShieldCheck className="w-5 h-5 flex-shrink-0 mt-0.5" />
        You created this project — you cannot approve or reject it.
      </div>
    )
  }

  const take = async (stage) => {
    setBusy(true)
    setError('')
    try {
      await api.transitionStage(project.project_id, stage, comment)
      setComment('')
      onTransition()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 space-y-3">
      <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
        <ChevronRight className="w-4 h-4 text-emerald-600" />
        Available Actions
      </h3>
      {error && (
        <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
      )}
      <input
        type="text"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Add a comment (optional)…"
        className="w-full text-sm border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-400"
      />
      <div className="flex flex-wrap gap-2">
        {actions.map(({ label, stage, danger }) => (
          <button
            key={stage}
            disabled={busy}
            onClick={() => take(stage)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl transition-colors disabled:opacity-60 ${
              danger
                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                : 'bg-emerald-600 text-white hover:bg-emerald-700'
            }`}
          >
            {danger ? <XCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
            {busy ? '…' : label}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Milestone Row ─────────────────────────────────────────────────────────

function MilestoneRow({ milestone, projectId, csrRole, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [status, setStatus]   = useState(milestone.status)
  const [budgetUsed, setBudgetUsed] = useState(milestone.budget_used || 0)
  const [busy, setBusy]       = useState(false)

  const canEdit = ['csr_head', 'project_manager'].includes(csrRole)

  const save = async () => {
    setBusy(true)
    try {
      await api.updateMilestone(projectId, milestone.milestone_id, {
        status,
        budget_used: parseFloat(budgetUsed) || 0,
        completion_date: status === 'completed' ? new Date().toISOString().split('T')[0] : null,
      })
      setEditing(false)
      onUpdate()
    } catch (err) {
      alert(err.message)
    } finally {
      setBusy(false)
    }
  }

  const isOverdue =
    milestone.status !== 'completed' &&
    milestone.target_date &&
    new Date(milestone.target_date) < new Date()

  return (
    <div className={`p-4 rounded-xl border ${isOverdue ? 'border-red-200 bg-red-50' : 'border-gray-100 bg-gray-50'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-sm font-semibold text-gray-900">{milestone.title}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${MILESTONE_STATUS_COLOR[milestone.status] || 'bg-gray-100 text-gray-600'}`}>
              {milestone.status}
            </span>
            {isOverdue && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                overdue
              </span>
            )}
          </div>
          {milestone.description && (
            <p className="text-xs text-gray-500 mb-1">{milestone.description}</p>
          )}
          <div className="flex flex-wrap gap-3 text-xs text-gray-400">
            {milestone.target_date && (
              <span className="flex items-center gap-1">
                <CalendarDays className="w-3 h-3" />
                Due {milestone.target_date}
              </span>
            )}
            {milestone.budget_allocated > 0 && (
              <span className="flex items-center gap-1">
                <DollarSign className="w-3 h-3" />
                ₹{Number(milestone.budget_allocated).toLocaleString()} allocated
                {milestone.budget_used > 0 && ` · ₹${Number(milestone.budget_used).toLocaleString()} used`}
              </span>
            )}
          </div>
          {milestone.deliverables?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {milestone.deliverables.map((d, i) => (
                <span key={i} className="px-2 py-0.5 bg-gray-200 text-gray-600 text-xs rounded-lg">{d}</span>
              ))}
            </div>
          )}
        </div>
        {canEdit && !editing && (
          <button
            onClick={() => setEditing(true)}
            className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
          >
            <Edit3 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {editing && (
        <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-400 bg-white"
              >
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="overdue">Overdue</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Budget Used (₹)</label>
              <input
                type="number"
                value={budgetUsed}
                onChange={(e) => setBudgetUsed(e.target.value)}
                min="0"
                className="w-full text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-400"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              disabled={busy}
              onClick={save}
              className="px-3 py-1.5 bg-emerald-600 text-white text-xs font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-60"
            >
              {busy ? 'Saving…' : 'Save'}
            </button>
            <button
              onClick={() => setEditing(false)}
              className="px-3 py-1.5 bg-gray-100 text-gray-600 text-xs font-semibold rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────

export default function ProjectDetail() {
  const { id }              = useParams()
  const { csrRole, profile } = useAuth()
  const navigate            = useNavigate()

  const [project, setProject]   = useState(null)
  const [history, setHistory]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [showHistory, setShowHistory] = useState(false)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const p = await api.getProject(id)
      setProject(p)
      // Load history if csr_head or approver
      if (['csr_head', 'approver'].includes(csrRole)) {
        try {
          const h = await api.getProjectHistory(id)
          setHistory(h)
        } catch { /* non-fatal */ }
      }
    } catch (err) {
      setError(err.message || 'Project not found.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (id) load() }, [id])

  const backPath = csrRole === 'csr_head'        ? '/csr/head'
                : csrRole === 'project_manager'  ? '/csr/pm'
                : '/csr/approver'

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600" />
          <p className="text-sm text-gray-500">Loading project…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto mt-16 text-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto">
          <AlertTriangle className="w-8 h-8 text-red-500" />
        </div>
        <h2 className="text-xl font-bold text-gray-900">Project not found</h2>
        <p className="text-sm text-gray-500">{error}</p>
        <Link
          to={backPath}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white text-sm font-semibold rounded-xl hover:bg-emerald-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>
      </div>
    )
  }

  if (!project) return null

  const completedMilestones = (project.milestones || []).filter(m => m.status === 'completed').length
  const totalMilestones     = (project.milestones || []).length
  const progressPct         = totalMilestones > 0 ? Math.round((completedMilestones / totalMilestones) * 100) : 0

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* ── Header ── */}
      <div className="flex items-start gap-3">
        <Link
          to={backPath}
          className="p-2 rounded-xl hover:bg-gray-100 transition-colors text-gray-500 flex-shrink-0 mt-1"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap mb-1">
            <h1 className="text-2xl font-bold text-gray-900 truncate">{project.title}</h1>
            <StageBadge stage={project.stage} label={project.stage_label} />
          </div>
          <p className="text-sm text-gray-500 capitalize">{project.domain?.replace('_', ' ')}</p>
        </div>
      </div>

      {/* ── Stage actions ── */}
      <StageActions project={project} csrRole={csrRole} onTransition={load} />

      {/* ── Info grid ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <p className="text-xs text-gray-400 font-medium mb-1 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5" /> Budget
          </p>
          <p className="text-xl font-bold text-gray-900">
            {project.budget != null ? `₹${Number(project.budget).toLocaleString('en-IN')}` : '—'}
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <p className="text-xs text-gray-400 font-medium mb-1 flex items-center gap-1.5">
            <CheckSquare className="w-3.5 h-3.5" /> Milestone Progress
          </p>
          <p className="text-xl font-bold text-gray-900">{progressPct}%</p>
          <div className="mt-2 h-1.5 bg-gray-100 rounded-full">
            <div
              className="h-1.5 bg-emerald-500 rounded-full transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-1">{completedMilestones}/{totalMilestones} done</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <p className="text-xs text-gray-400 font-medium mb-1 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" /> Team
          </p>
          <p className="text-xs text-gray-600 mt-1">
            PM: <span className="font-medium">{project.assigned_pm ? '✓ Assigned' : 'Not assigned'}</span>
          </p>
          <p className="text-xs text-gray-600">
            Approver: <span className="font-medium">{project.assigned_approver ? '✓ Assigned' : 'Not assigned'}</span>
          </p>
        </div>
      </div>

      {/* ── Description ── */}
      {project.description && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Description</h3>
          <p className="text-sm text-gray-600 leading-relaxed">{project.description}</p>
        </div>
      )}

      {/* ── Milestones ── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Flag className="w-4 h-4 text-emerald-600" />
            Milestones
            {totalMilestones > 0 && (
              <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                {totalMilestones}
              </span>
            )}
          </h3>
        </div>

        {totalMilestones === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No milestones defined for this project.</p>
        ) : (
          <div className="space-y-2">
            {project.milestones.map((m) => (
              <MilestoneRow
                key={m.milestone_id}
                milestone={m}
                projectId={project.project_id}
                csrRole={csrRole}
                onUpdate={load}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Stage History (csr_head + approver) ── */}
      {['csr_head', 'approver'].includes(csrRole) && history.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-2 text-sm font-semibold text-gray-700 w-full text-left"
          >
            <History className="w-4 h-4 text-gray-400" />
            Audit Trail
            <span className="text-xs text-gray-400 font-normal ml-1">({history.length} events)</span>
            <ChevronRight className={`w-4 h-4 text-gray-400 ml-auto transition-transform ${showHistory ? 'rotate-90' : ''}`} />
          </button>

          {showHistory && (
            <div className="mt-4 space-y-2">
              {[...history].reverse().map((h, i) => (
                <div key={i} className="flex items-start gap-3 text-xs text-gray-600">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0 mt-1.5" />
                  <div>
                    <span className="font-medium capitalize">
                      {h.from_stage ? `${h.from_stage} → ` : ''}{h.to_stage}
                    </span>
                    <span className="text-gray-400 ml-2">
                      by {h.actor_role} · {new Date(h.at).toLocaleString()}
                    </span>
                    {h.comment && <p className="text-gray-500 mt-0.5 italic">"{h.comment}"</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
