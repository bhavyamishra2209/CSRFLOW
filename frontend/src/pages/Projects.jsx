import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import {
  FolderGit2,
  Plus,
  Search,
  Calendar,
  Building2,
  Tag,
  IndianRupee,
  MapPin,
  AlertCircle,
  X,
  ArrowRight,
  Clock,
  CheckCircle2,
} from 'lucide-react'

export const STAGE_CONFIG = {
  DRAFT: { label: 'Draft', color: 'bg-gray-100 text-gray-800 border-gray-300' },
  SUBMITTED: { label: 'Submitted', color: 'bg-blue-100 text-blue-800 border-blue-300' },
  UNDER_EVALUATION: { label: 'Under Evaluation', color: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  APPROVED: { label: 'Approved', color: 'bg-indigo-100 text-indigo-800 border-indigo-300' },
  FUNDED: { label: 'Funded', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
  IN_PROGRESS: { label: 'In Progress', color: 'bg-purple-100 text-purple-800 border-purple-300' },
  UNDER_REVIEW: { label: 'Under Review', color: 'bg-orange-100 text-orange-800 border-orange-300' },
  COMPLETED: { label: 'Completed', color: 'bg-green-100 text-green-800 border-green-300' },
  CLOSED: { label: 'Closed', color: 'bg-slate-200 text-slate-700 border-slate-400' },
}

function Projects() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [stageFilter, setStageFilter] = useState('ALL')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  // New Project Form State
  const [formData, setFormData] = useState({
    title: '',
    organization_name: '',
    sector: '',
    budget: '',
    currency: 'INR',
    location: '',
    description: '',
  })

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await api.projectsList()
      setProjects(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to load projects:', err)
      setError(err.message || 'Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSubmit = async (e) => {
    e.preventDefault()
    if (!formData.title.trim() || !formData.organization_name.trim() || !formData.sector.trim()) {
      setCreateError('Title, organization name, and sector are required.')
      return
    }

    try {
      setCreating(true)
      setCreateError('')
      const payload = {
        title: formData.title.trim(),
        organization_name: formData.organization_name.trim(),
        sector: formData.sector.trim(),
        budget: formData.budget ? parseFloat(formData.budget) : 0.0,
        currency: formData.currency.trim() || 'INR',
        location: formData.location.trim() || null,
        description: formData.description.trim(),
      }
      const newProject = await api.createProject(payload)
      setProjects([newProject, ...projects])
      setIsCreateOpen(false)
      setFormData({
        title: '',
        organization_name: '',
        sector: '',
        budget: '',
        currency: 'INR',
        location: '',
        description: '',
      })
    } catch (err) {
      console.error('Project creation failed:', err)
      setCreateError(err.message || 'Failed to create project')
    } finally {
      setCreating(false)
    }
  }

  const filteredProjects = projects.filter((p) => {
    const matchesSearch =
      p.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.project_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.organization_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.sector?.toLowerCase().includes(searchTerm.toLowerCase())

    if (stageFilter === 'ALL') return matchesSearch
    return matchesSearch && p.current_stage === stageFilter
  })

  const formatCurrency = (amount, currency = 'INR') => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency || 'INR',
      maximumFractionDigits: 0,
    }).format(amount || 0)
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">CSR Projects</h1>
          <p className="text-gray-600">
            Manage lifecycle progression, document links, and verification for CSR initiatives
          </p>
        </div>
        <button
          onClick={() => {
            setCreateError('')
            setIsCreateOpen(true)
          }}
          className="btn btn-primary mt-4 md:mt-0 flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>New CSR Project</span>
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={loadProjects}
              className="mt-2 text-sm text-red-700 underline hover:text-red-800"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      {/* Filters and search */}
      <div className="card p-4 mb-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by code, title, organization, sector..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input pl-10 w-full"
            />
          </div>

          <div className="text-sm text-gray-500">
            Showing <span className="font-semibold text-gray-800">{filteredProjects.length}</span> of{' '}
            <span className="font-semibold text-gray-800">{projects.length}</span> projects
          </div>
        </div>

        {/* Stage Filter Pills */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-100">
          <button
            onClick={() => setStageFilter('ALL')}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              stageFilter === 'ALL'
                ? 'bg-primary-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All Stages ({projects.length})
          </button>
          {Object.keys(STAGE_CONFIG).map((stageKey) => {
            const count = projects.filter((p) => p.current_stage === stageKey).length
            return (
              <button
                key={stageKey}
                onClick={() => setStageFilter(stageKey)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  stageFilter === stageKey
                    ? 'bg-primary-600 text-white shadow-sm'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {STAGE_CONFIG[stageKey].label} ({count})
              </button>
            )
          })}
        </div>
      </div>

      {/* Project list */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="card p-12 text-center">
          <FolderGit2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {searchTerm || stageFilter !== 'ALL' ? 'No projects match your filter' : 'No CSR Projects yet'}
          </h3>
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            {searchTerm || stageFilter !== 'ALL'
              ? 'Try adjusting your search criteria or stage filter.'
              : 'Create your first CSR project to begin managing its end-to-end lifecycle and linking documentation.'}
          </p>
          {stageFilter === 'ALL' && !searchTerm && (
            <button
              onClick={() => setIsCreateOpen(true)}
              className="btn btn-primary inline-flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Create Project</span>
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project) => {
            const stageInfo = STAGE_CONFIG[project.current_stage] || {
              label: project.current_stage,
              color: 'bg-gray-100 text-gray-800',
            }

            return (
              <Link
                key={project.project_id}
                to={`/projects/${project.project_id}`}
                className="card p-6 hover:shadow-lg transition-all flex flex-col justify-between group border border-gray-200 hover:border-primary-400"
              >
                <div>
                  {/* Top Bar: Code + Stage */}
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-xs font-bold text-primary-700 bg-primary-50 px-2 py-1 rounded border border-primary-200">
                      {project.project_code}
                    </span>
                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${stageInfo.color}`}>
                      {stageInfo.label}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="text-lg font-bold text-gray-900 group-hover:text-primary-600 transition-colors mb-2 line-clamp-2">
                    {project.title}
                  </h3>

                  {/* Description preview */}
                  {project.description && (
                    <p className="text-xs text-gray-500 mb-4 line-clamp-2">
                      {project.description}
                    </p>
                  )}

                  {/* Metadata fields */}
                  <div className="space-y-1.5 text-xs text-gray-600 mb-4">
                    <div className="flex items-center space-x-2">
                      <Building2 className="w-3.5 h-3.5 text-gray-400" />
                      <span className="truncate">{project.organization_name}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Tag className="w-3.5 h-3.5 text-gray-400" />
                      <span>{project.sector}</span>
                    </div>
                    {project.location && (
                      <div className="flex items-center space-x-2">
                        <MapPin className="w-3.5 h-3.5 text-gray-400" />
                        <span className="truncate">{project.location}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Bottom Bar: Budget + Date + Link */}
                <div className="pt-4 border-t border-gray-100 flex items-center justify-between mt-2">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold block">
                      Budget
                    </span>
                    <span className="text-sm font-bold text-gray-900">
                      {formatCurrency(project.budget, project.currency)}
                    </span>
                  </div>

                  <div className="flex items-center space-x-1 text-primary-600 text-xs font-semibold group-hover:translate-x-1 transition-transform">
                    <span>View</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}

      {/* Create Project Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl max-w-xl w-full p-6 my-8 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-4 border-b border-gray-200">
              <div className="flex items-center space-x-2">
                <FolderGit2 className="w-6 h-6 text-primary-600" />
                <h2 className="text-xl font-bold text-gray-900">Create New CSR Project</h2>
              </div>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {createError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{createError}</p>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Project Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Clean Water & Sanitation for District Schools"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="input w-full"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Partner / NGO Organization <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., Seva Foundation"
                    value={formData.organization_name}
                    onChange={(e) => setFormData({ ...formData, organization_name: e.target.value })}
                    className="input w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sector <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., Healthcare, Education, Environment"
                    value={formData.sector}
                    onChange={(e) => setFormData({ ...formData, sector: e.target.value })}
                    className="input w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Allocated Budget
                  </label>
                  <input
                    type="number"
                    step="1000"
                    min="0"
                    placeholder="e.g., 1500000"
                    value={formData.budget}
                    onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
                    className="input w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
                  <input
                    type="text"
                    value={formData.currency}
                    onChange={(e) => setFormData({ ...formData, currency: e.target.value.toUpperCase() })}
                    className="input w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Location / Region
                </label>
                <input
                  type="text"
                  placeholder="e.g., Pune, Maharashtra"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Project Description
                </label>
                <textarea
                  rows="3"
                  placeholder="Summarize project objectives, expected beneficiaries, and scope..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input w-full"
                ></textarea>
              </div>

              <div className="pt-4 border-t border-gray-200 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="btn btn-secondary text-gray-700 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="btn btn-primary flex items-center space-x-2"
                >
                  {creating ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Creating...</span>
                    </>
                  ) : (
                    <span>Create Project</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Projects
