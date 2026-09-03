import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { STAGE_CONFIG } from './Projects'
import {
  ArrowLeft,
  FolderGit2,
  Building2,
  Tag,
  MapPin,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Paperclip,
  Trash2,
  History,
  ShieldCheck,
  Send,
  Plus,
  X,
  ExternalLink,
  Info,
} from 'lucide-react'

const LIFECYCLE_ORDER = [
  'DRAFT',
  'SUBMITTED',
  'UNDER_EVALUATION',
  'APPROVED',
  'FUNDED',
  'IN_PROGRESS',
  'UNDER_REVIEW',
  'COMPLETED',
  'CLOSED',
]

function ProjectDetail() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [allowedStages, setAllowedStages] = useState([])
  const [linkedDocs, setLinkedDocs] = useState([])
  const [auditLog, setAuditLog] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Transition stage form
  const [selectedTargetStage, setSelectedTargetStage] = useState('')
  const [transitionComments, setTransitionComments] = useState('')
  const [transitioning, setTransitioning] = useState(false)
  const [transitionError, setTransitionError] = useState('')

  // Document linking modal
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false)
  const [availableDocs, setAvailableDocs] = useState([])
  const [selectedDocId, setSelectedDocId] = useState('')
  const [linkingDoc, setLinkingDoc] = useState(false)
  const [linkDocError, setLinkDocError] = useState('')

  // Active tab (history vs audit)
  const [activeTab, setActiveTab] = useState('history')

  useEffect(() => {
    loadAllProjectData()
  }, [id])

  const loadAllProjectData = async () => {
    try {
      setLoading(true)
      setError('')
      const [projData, allowedData, docsData, auditData] = await Promise.all([
        api.getProject(id),
        api.getAllowedStages(id).catch(() => []),
        api.getProjectDocuments(id).catch(() => []),
        api.getProjectAudit(id).catch(() => []),
      ])

      setProject(projData)
      setAllowedStages(allowedData || [])
      setLinkedDocs(docsData || [])
      setAuditLog(auditData || [])

      if (allowedData && allowedData.length > 0) {
        setSelectedTargetStage(allowedData[0])
      } else {
        setSelectedTargetStage('')
      }
    } catch (err) {
      console.error('Failed to load project details:', err)
      setError(err.message || 'Failed to load project')
    } finally {
      setLoading(false)
    }
  }

  const handleTransitionSubmit = async (e) => {
    e.preventDefault()
    if (!selectedTargetStage) return

    try {
      setTransitioning(true)
      setTransitionError('')
      const updated = await api.transitionProjectStage(
        id,
        selectedTargetStage,
        transitionComments.trim() || null
      )
      setProject(updated)
      setTransitionComments('')

      // Refresh allowed stages, history, and audit
      const [allowedData, auditData] = await Promise.all([
        api.getAllowedStages(id).catch(() => []),
        api.getProjectAudit(id).catch(() => []),
      ])
      setAllowedStages(allowedData || [])
      setAuditLog(auditData || [])
      if (allowedData && allowedData.length > 0) {
        setSelectedTargetStage(allowedData[0])
      } else {
        setSelectedTargetStage('')
      }
    } catch (err) {
      console.error('Stage transition failed:', err)
      setTransitionError(err.message || 'Stage transition failed')
    } finally {
      setTransitioning(false)
    }
  }

  const handleOpenLinkModal = async () => {
    setLinkDocError('')
    setSelectedDocId('')
    setIsLinkModalOpen(true)
    try {
      const data = await api.documentsList()
      const allDocs = Array.isArray(data) ? data : data.documents || []
      // Filter out docs already linked
      const alreadyLinkedIds = new Set(project?.linked_document_ids || [])
      const unlinked = allDocs.filter((d) => !alreadyLinkedIds.has(d.document_id))
      setAvailableDocs(unlinked)
      if (unlinked.length > 0) {
        setSelectedDocId(unlinked[0].document_id)
      }
    } catch (err) {
      console.error('Failed to load available documents:', err)
      setLinkDocError('Failed to load document list')
    }
  }

  const handleLinkSubmit = async (e) => {
    e.preventDefault()
    if (!selectedDocId) return

    try {
      setLinkingDoc(true)
      setLinkDocError('')
      const updated = await api.linkProjectDocument(id, selectedDocId)
      setProject(updated)
      setIsLinkModalOpen(false)

      // Refresh docs and audit
      const [docsData, auditData] = await Promise.all([
        api.getProjectDocuments(id).catch(() => []),
        api.getProjectAudit(id).catch(() => []),
      ])
      setLinkedDocs(docsData || [])
      setAuditLog(auditData || [])
    } catch (err) {
      console.error('Failed to link document:', err)
      setLinkDocError(err.message || 'Failed to link document')
    } finally {
      setLinkingDoc(false)
    }
  }

  const handleUnlinkDocument = async (docId) => {
    if (!window.confirm('Are you sure you want to unlink this document from the project?')) {
      return
    }

    try {
      const updated = await api.unlinkProjectDocument(id, docId)
      setProject(updated)

      // Refresh docs and audit
      const [docsData, auditData] = await Promise.all([
        api.getProjectDocuments(id).catch(() => []),
        api.getProjectAudit(id).catch(() => []),
      ])
      setLinkedDocs(docsData || [])
      setAuditLog(auditData || [])
    } catch (err) {
      console.error('Failed to unlink document:', err)
      alert(err.message || 'Failed to unlink document')
    }
  }

  const formatCurrency = (amount, currency = 'INR') => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency || 'INR',
      maximumFractionDigits: 0,
    }).format(amount || 0)
  }

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card p-12 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Project</h3>
          <p className="text-gray-600 mb-6">{error || 'Project not found'}</p>
          <Link to="/projects" className="btn btn-primary">
            Back to Projects
          </Link>
        </div>
      </div>
    )
  }

  const currentStageInfo = STAGE_CONFIG[project.current_stage] || {
    label: project.current_stage,
    color: 'bg-gray-100 text-gray-800 border-gray-300',
  }

  const currentStageIndex = LIFECYCLE_ORDER.indexOf(project.current_stage)

  return (
    <div className="max-w-6xl mx-auto pb-12">
      {/* Back button */}
      <Link
        to="/projects"
        className="inline-flex items-center space-x-2 text-primary-600 hover:text-primary-700 mb-4 text-sm font-medium"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Projects</span>
      </Link>

      {/* Header Banner */}
      <div className="card p-6 mb-6 border border-gray-200">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2.5 mb-2">
              <span className="font-mono text-xs font-bold text-primary-700 bg-primary-50 px-2.5 py-1 rounded border border-primary-200">
                {project.project_code}
              </span>
              <span className={`text-xs font-semibold px-3 py-1 rounded-full border ${currentStageInfo.color}`}>
                {currentStageInfo.label}
              </span>
            </div>

            <h1 className="text-2xl font-bold text-gray-900 mb-3">{project.title}</h1>

            <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600">
              <div className="flex items-center space-x-1.5">
                <Building2 className="w-4 h-4 text-gray-400" />
                <span className="font-medium text-gray-800">{project.organization_name}</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <Tag className="w-4 h-4 text-gray-400" />
                <span>{project.sector}</span>
              </div>
              {project.location && (
                <div className="flex items-center space-x-1.5">
                  <MapPin className="w-4 h-4 text-gray-400" />
                  <span>{project.location}</span>
                </div>
              )}
              <div className="flex items-center space-x-1.5">
                <Calendar className="w-4 h-4 text-gray-400" />
                <span>Created {formatDateTime(project.created_at)}</span>
              </div>
            </div>
          </div>

          <div className="text-right lg:border-l lg:border-gray-200 lg:pl-6">
            <span className="text-xs uppercase tracking-wider text-gray-400 font-semibold block mb-1">
              Project Budget
            </span>
            <span className="text-2xl font-black text-gray-900">
              {formatCurrency(project.budget, project.currency)}
            </span>
            <span className="text-[11px] text-gray-500 block mt-0.5">Allocated CSR Funds</span>
          </div>
        </div>
      </div>

      {/* ── 9-STAGE LIFECYCLE PROGRESSION TRACKER ── */}
      <div className="card p-6 mb-6">
        <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4 flex items-center space-x-2">
          <Clock className="w-4 h-4 text-primary-600" />
          <span>Lifecycle Progression (9 Stages)</span>
        </h2>

        <div className="overflow-x-auto pb-2">
          <div className="flex items-center min-w-[700px] justify-between relative">
            {/* Connecting line */}
            <div className="absolute top-4 left-6 right-6 h-0.5 bg-gray-200 -z-0"></div>

            {LIFECYCLE_ORDER.map((stageKey, index) => {
              const isCurrent = stageKey === project.current_stage
              const isPast = index < currentStageIndex && project.current_stage !== 'CLOSED'
              const isClosed = project.current_stage === 'CLOSED'
              const stageConfig = STAGE_CONFIG[stageKey]

              return (
                <div key={stageKey} className="flex flex-col items-center relative z-10">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                      isCurrent
                        ? 'bg-primary-600 text-white ring-4 ring-primary-100 shadow-md scale-110'
                        : isPast
                        ? 'bg-green-500 text-white'
                        : isClosed && stageKey === 'CLOSED'
                        ? 'bg-slate-700 text-white ring-4 ring-slate-200'
                        : 'bg-white border-2 border-gray-300 text-gray-400'
                    }`}
                  >
                    {isPast ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      index + 1
                    )}
                  </div>
                  <span
                    className={`text-[11px] font-medium mt-2 text-center max-w-[70px] ${
                      isCurrent
                        ? 'text-primary-700 font-bold'
                        : isPast
                        ? 'text-gray-800 font-semibold'
                        : 'text-gray-400'
                    }`}
                  >
                    {stageConfig.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Details + Linked Docs */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description Card */}
          <div className="card p-6">
            <h2 className="text-base font-bold text-gray-900 mb-3">Project Overview</h2>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {project.description || 'No detailed description provided for this project.'}
            </p>
          </div>

          {/* Linked Documents Card */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Paperclip className="w-5 h-5 text-primary-600" />
                <h2 className="text-base font-bold text-gray-900">
                  Linked Documentation ({linkedDocs.length})
                </h2>
              </div>
              <button
                onClick={handleOpenLinkModal}
                className="btn btn-sm btn-primary flex items-center space-x-1.5"
              >
                <Plus className="w-4 h-4" />
                <span>Attach Document</span>
              </button>
            </div>

            {linkedDocs.length === 0 ? (
              <div className="text-center py-8 border-2 border-dashed border-gray-200 rounded-lg">
                <FileText className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-600">No documents linked to this project yet.</p>
                <button
                  onClick={handleOpenLinkModal}
                  className="mt-3 text-xs text-primary-600 font-semibold hover:underline"
                >
                  Link an existing document
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {linkedDocs.map((doc) => (
                  <div
                    key={doc.document_id}
                    className="flex items-center justify-between p-3.5 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center space-x-3 min-w-0 flex-1">
                      <div className="bg-primary-100 p-2 rounded">
                        <FileText className="w-5 h-5 text-primary-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center space-x-2">
                          <Link
                            to={`/documents/${doc.document_id}`}
                            className="text-sm font-semibold text-gray-900 hover:text-primary-600 truncate flex items-center space-x-1"
                          >
                            <span>{doc.filename}</span>
                            <ExternalLink className="w-3.5 h-3.5 text-gray-400" />
                          </Link>
                        </div>
                        <div className="flex items-center space-x-3 text-xs text-gray-500 mt-0.5">
                          <span className="badge badge-blue text-[10px] py-0.5">{doc.document_type}</span>
                          {doc.upload_date && (
                            <span>Uploaded {new Date(doc.upload_date).toLocaleDateString()}</span>
                          )}
                          {doc.verification_status && (
                            <span className="font-semibold text-green-700">
                              {doc.verification_status}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleUnlinkDocument(doc.document_id)}
                      title="Unlink document"
                      className="ml-3 p-1.5 text-gray-400 hover:text-red-600 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Stage History & Audit Trail Tabs */}
          <div className="card p-6">
            <div className="flex border-b border-gray-200 mb-4">
              <button
                onClick={() => setActiveTab('history')}
                className={`pb-3 px-4 text-sm font-semibold flex items-center space-x-2 border-b-2 transition-colors ${
                  activeTab === 'history'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <History className="w-4 h-4" />
                <span>Stage History ({project.stage_history?.length || 0})</span>
              </button>

              <button
                onClick={() => setActiveTab('audit')}
                className={`pb-3 px-4 text-sm font-semibold flex items-center space-x-2 border-b-2 transition-colors ${
                  activeTab === 'audit'
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Audit Trail ({auditLog.length})</span>
              </button>
            </div>

            {/* Stage History Timeline */}
            {activeTab === 'history' && (
              <div className="space-y-4">
                {project.stage_history && project.stage_history.length > 0 ? (
                  project.stage_history.map((entry, idx) => (
                    <div key={idx} className="flex items-start space-x-3 text-xs border-l-2 border-primary-400 pl-4 py-1">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-gray-900">
                            {entry.from_stage ? `${entry.from_stage} → ${entry.to_stage}` : entry.to_stage}
                          </span>
                          <span className="text-gray-400">•</span>
                          <span className="text-gray-500">{formatDateTime(entry.changed_at)}</span>
                        </div>
                        {entry.comments && (
                          <p className="text-gray-700 mt-1 italic bg-gray-50 p-2 rounded">
                            "{entry.comments}"
                          </p>
                        )}
                        <p className="text-gray-400 text-[10px] mt-0.5">By {entry.changed_by}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-gray-500">No stage history recorded.</p>
                )}
              </div>
            )}

            {/* Audit Trail Timeline */}
            {activeTab === 'audit' && (
              <div className="space-y-3">
                {auditLog.length > 0 ? (
                  auditLog.map((audit) => (
                    <div key={audit.audit_id} className="p-3 bg-gray-50 rounded border border-gray-200 text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-gray-900 font-mono text-[11px]">
                          {audit.action}
                        </span>
                        <span className="text-gray-500">{formatDateTime(audit.performed_at)}</span>
                      </div>
                      <p className="text-gray-600 text-[11px] mb-1">Actor: {audit.performed_by}</p>
                      {audit.details && Object.keys(audit.details).length > 0 && (
                        <pre className="bg-white p-2 rounded text-[10px] font-mono text-gray-700 overflow-x-auto border border-gray-200">
                          {JSON.stringify(audit.details, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-gray-500">No audit records found.</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (1 Col): Stage Transition Action Panel */}
        <div className="space-y-6">
          <div className="card p-6 border-t-4 border-primary-600">
            <h2 className="text-base font-bold text-gray-900 mb-1 flex items-center space-x-2">
              <Send className="w-4 h-4 text-primary-600" />
              <span>Lifecycle Stage Action</span>
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              Current stage is <strong className="text-gray-800">{currentStageInfo.label}</strong>.
            </p>

            {transitionError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-red-700">{transitionError}</p>
              </div>
            )}

            {project.current_stage === 'CLOSED' ? (
              <div className="bg-slate-100 border border-slate-300 rounded-lg p-4 text-center">
                <p className="text-xs text-slate-700 font-medium">
                  This project has reached the terminal <strong>CLOSED</strong> stage. No further lifecycle transitions are allowed.
                </p>
              </div>
            ) : allowedStages.length === 0 ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-xs text-yellow-800">
                No immediate transitions available for this stage.
              </div>
            ) : (
              <form onSubmit={handleTransitionSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Target Lifecycle Stage
                  </label>
                  <select
                    value={selectedTargetStage}
                    onChange={(e) => setSelectedTargetStage(e.target.value)}
                    className="input w-full text-xs font-medium"
                  >
                    {allowedStages.map((stage) => (
                      <option key={stage} value={stage}>
                        {STAGE_CONFIG[stage]?.label || stage}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Transition Comments / Rationale
                  </label>
                  <textarea
                    rows="3"
                    placeholder="Enter reason or comments for this stage transition..."
                    value={transitionComments}
                    onChange={(e) => setTransitionComments(e.target.value)}
                    className="input w-full text-xs"
                  ></textarea>
                </div>

                <button
                  type="submit"
                  disabled={transitioning || !selectedTargetStage}
                  className="w-full btn btn-primary flex items-center justify-center space-x-2 py-2.5 text-xs font-semibold"
                >
                  {transitioning ? (
                    <>
                      <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white"></div>
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Transition to {STAGE_CONFIG[selectedTargetStage]?.label || selectedTargetStage}</span>
                    </>
                  )}
                </button>
              </form>
            )}
          </div>

          {/* Quick Info Box */}
          <div className="card p-5 bg-blue-50 border border-blue-200">
            <div className="flex items-start space-x-2.5">
              <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-blue-900 leading-relaxed">
                <p className="font-semibold mb-1">About CSR Lifecycle Management</p>
                <p>
                  Every stage transition is strictly validated against the 9-stage CSR state machine and permanently recorded in the project's audit trail.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Attach Document Modal */}
      {isLinkModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <div className="flex items-center space-x-2">
                <Paperclip className="w-5 h-5 text-primary-600" />
                <h3 className="text-lg font-bold text-gray-900">Attach Document to Project</h3>
              </div>
              <button
                onClick={() => setIsLinkModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {linkDocError && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-red-700">{linkDocError}</p>
              </div>
            )}

            <form onSubmit={handleLinkSubmit} className="mt-4 space-y-4">
              {availableDocs.length === 0 ? (
                <div className="py-6 text-center text-xs text-gray-500">
                  <p>No unlinked documents found in your library.</p>
                  <Link to="/upload" className="text-primary-600 font-semibold hover:underline mt-2 inline-block">
                    Upload new document
                  </Link>
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Select Document
                  </label>
                  <select
                    value={selectedDocId}
                    onChange={(e) => setSelectedDocId(e.target.value)}
                    className="input w-full text-xs font-medium"
                    required
                  >
                    {availableDocs.map((doc) => (
                      <option key={doc.document_id} value={doc.document_id}>
                        {doc.filename} ({doc.document_type || 'Unknown'})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="pt-3 border-t border-gray-200 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsLinkModalOpen(false)}
                  className="btn btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={linkingDoc || availableDocs.length === 0}
                  className="btn btn-primary text-xs flex items-center space-x-1.5"
                >
                  {linkingDoc ? <span>Linking...</span> : <span>Attach Document</span>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProjectDetail
