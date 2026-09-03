import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../../api/client'
import {
  ArrowLeft, PlusCircle, Trash2, AlertTriangle, CheckCircle,
  FolderOpen, DollarSign, CalendarDays, ClipboardList,
} from 'lucide-react'

const DOMAINS = [
  { value: 'education',        label: '📚 Education' },
  { value: 'healthcare',       label: '🏥 Healthcare' },
  { value: 'environment',      label: '🌿 Environment' },
  { value: 'community',        label: '🤝 Community' },
  { value: 'livelihood',       label: '💼 Livelihood' },
  { value: 'water_sanitation', label: '💧 Water & Sanitation' },
  { value: 'disaster_relief',  label: '🆘 Disaster Relief' },
  { value: 'other',            label: '🔹 Other' },
]

const emptyMilestone = () => ({
  _id:              Date.now() + Math.random(),
  title:            '',
  description:      '',
  target_date:      '',
  budget_allocated: '',
  deliverables:     '',
})

export default function CreateProject() {
  const navigate = useNavigate()

  const [form, setForm] = useState({
    title:       '',
    domain:      '',
    description: '',
    budget:      '',
  })
  const [milestones, setMilestones] = useState([])
  const [busy, setBusy]     = useState(false)
  const [error, setError]   = useState('')
  const [success, setSuccess] = useState('')

  // ── Field helpers ─────────────────────────────────────────────────────────
  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  const setMs = (id, field) => (e) =>
    setMilestones((ms) =>
      ms.map((m) => (m._id === id ? { ...m, [field]: e.target.value } : m))
    )

  const addMilestone    = () => setMilestones((ms) => [...ms, emptyMilestone()])
  const removeMilestone = (id) => setMilestones((ms) => ms.filter((m) => m._id !== id))

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!form.title.trim()) { setError('Project title is required.'); return }
    if (!form.domain)       { setError('Please select a domain.'); return }

    // Validate milestones
    for (const m of milestones) {
      if (!m.title.trim())       { setError('Each milestone must have a title.'); return }
      if (!m.target_date)        { setError('Each milestone must have a target date.'); return }
    }

    const payload = {
      title:       form.title.trim(),
      domain:      form.domain,
      description: form.description.trim(),
      budget:      form.budget ? parseFloat(form.budget) : null,
      milestones:  milestones.map((m) => ({
        title:            m.title.trim(),
        description:      m.description.trim(),
        target_date:      m.target_date,
        budget_allocated: m.budget_allocated ? parseFloat(m.budget_allocated) : 0,
        deliverables:     m.deliverables
          ? m.deliverables.split(',').map((d) => d.trim()).filter(Boolean)
          : [],
      })),
    }

    setBusy(true)
    try {
      const project = await api.createProject(payload)
      setSuccess('Project created successfully!')
      setTimeout(() => navigate(`/csr/projects/${project.project_id}`), 1200)
    } catch (err) {
      setError(err.message || 'Failed to create project.')
    } finally {
      setBusy(false)
    }
  }

  // ── UI ────────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to="/csr/head"
          className="p-2 rounded-xl hover:bg-gray-100 transition-colors text-gray-500"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">New CSR Project</h1>
          <p className="text-sm text-gray-500">Fill in the details and add milestones</p>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-start gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700">
          <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">

        {/* ── Project details card ── */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-5">
          <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-emerald-600" />
            Project Details
          </h2>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Project Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.title}
              onChange={set('title')}
              required
              placeholder="e.g. Digital Literacy Programme — Rural Tamil Nadu"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </div>

          {/* Domain */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Domain <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {DOMAINS.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, domain: d.value }))}
                  className={`px-3 py-2 text-xs font-medium rounded-xl border transition-all text-left ${
                    form.domain === d.value
                      ? 'bg-emerald-600 text-white border-emerald-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-emerald-400'
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Description
            </label>
            <textarea
              value={form.description}
              onChange={set('description')}
              rows={3}
              placeholder="Brief overview of the project objectives and expected outcomes…"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Budget */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5 flex items-center gap-1.5">
              <DollarSign className="w-4 h-4 text-gray-400" />
              Total Budget (₹)
            </label>
            <input
              type="number"
              value={form.budget}
              onChange={set('budget')}
              min="0"
              step="1000"
              placeholder="e.g. 500000"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
            {form.budget && (
              <p className="mt-1 text-xs text-gray-400">
                = ₹{Number(form.budget).toLocaleString('en-IN')}
              </p>
            )}
          </div>
        </div>

        {/* ── Milestones card ── */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-emerald-600" />
              Milestones
              {milestones.length > 0 && (
                <span className="ml-1 px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded-full">
                  {milestones.length}
                </span>
              )}
            </h2>
            <button
              type="button"
              onClick={addMilestone}
              className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 hover:text-emerald-700 px-3 py-1.5 rounded-lg hover:bg-emerald-50 transition-colors"
            >
              <PlusCircle className="w-4 h-4" />
              Add Milestone
            </button>
          </div>

          {milestones.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-4">
              No milestones yet — click "Add Milestone" to track project checkpoints.
            </p>
          )}

          {milestones.map((m, idx) => (
            <div
              key={m._id}
              className="border border-gray-100 rounded-xl p-4 space-y-3 bg-gray-50"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500">
                  Milestone {idx + 1}
                </span>
                <button
                  type="button"
                  onClick={() => removeMilestone(m._id)}
                  className="p-1 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Title <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={m.title}
                    onChange={setMs(m._id, 'title')}
                    placeholder="e.g. Phase 1 — Setup"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                    <CalendarDays className="w-3.5 h-3.5" />
                    Target Date <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    value={m.target_date}
                    onChange={setMs(m._id, 'target_date')}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Budget Allocated (₹)
                  </label>
                  <input
                    type="number"
                    value={m.budget_allocated}
                    onChange={setMs(m._id, 'budget_allocated')}
                    min="0"
                    placeholder="0"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Deliverables (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={m.deliverables}
                    onChange={setMs(m._id, 'deliverables')}
                    placeholder="e.g. Report, Training session"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Description
                </label>
                <textarea
                  value={m.description}
                  onChange={setMs(m._id, 'description')}
                  rows={2}
                  placeholder="What needs to happen in this milestone?"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white resize-none"
                />
              </div>
            </div>
          ))}
        </div>

        {/* ── Actions ── */}
        <div className="flex items-center justify-between gap-3">
          <Link
            to="/csr/head"
            className="px-5 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={busy}
            className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            {busy ? 'Creating…' : 'Create Project'}
          </button>
        </div>
      </form>
    </div>
  )
}
