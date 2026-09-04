import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'
import {
  FolderPlus,
  Building2,
  FileCheck,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Send,
  Upload,
  UserCheck,
  Shield,
  Layers,
  DollarSign,
  Users,
  Edit3,
  RotateCcw,
  Sliders,
  UserPlus,
} from 'lucide-react'

function Dashboard() {
  const { activeRole, roleConfig, isAdmin, isPM, isAuditor } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // CSR Head state
  const [headProjectsData, setHeadProjectsData] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newProject, setNewProject] = useState({
    case_id: '',
    title: '',
    total_budget: '',
    assigned_pm_id: 'pm_exec_101',
    assigned_auditor_id: 'auditor_rev_201',
  })

  // User Management state
  const [usersList, setUsersList] = useState([])
  const [showUserModal, setShowUserModal] = useState(false)
  const [newUser, setNewUser] = useState({ user_id: '', name: '', email: '', role: 'project_manager' })

  // CSR Head Edit Project state
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingProject, setEditingProject] = useState(null)

  // CSR Head Admin Override state
  const [showOverrideModal, setShowOverrideModal] = useState(false)
  const [overrideData, setOverrideData] = useState({ case_id: '', target_stage: 'IN_PROGRESS', comments: '' })

  // PM state
  const [pmProjectsData, setPmProjectsData] = useState(null)
  const [selectedPmCase, setSelectedPmCase] = useState(null)
  const [newMilestone, setNewMilestone] = useState({
    title: '',
    target_date: '',
    allocated_budget: '',
    progress_percentage: 0,
    spent_amount: 0,
  })
  const [pmExecDoc, setPmExecDoc] = useState({
    filename: '',
    document_type: 'progress_report',
    raw_text: '',
  })
  const [pmSelectedFile, setPmSelectedFile] = useState(null)
  const [isUploadingDoc, setIsUploadingDoc] = useState(false)

  // Auditor state
  const [auditorProjectsData, setAuditorProjectsData] = useState(null)
  const [selectedAuditPack, setSelectedAuditPack] = useState(null)
  const [auditDecision, setAuditDecision] = useState({
    action: 'APPROVE',
    comments: '',
  })

  // Load data whenever activeRole changes
  useEffect(() => {
    loadRoleData()
  }, [activeRole])

  const loadRoleData = async () => {
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      if (activeRole === 'csr_head') {
        const data = await api.rbac.head.getAllProjects()
        setHeadProjectsData(data)
      } else if (activeRole === 'project_manager') {
        const data = await api.rbac.pm.getAssignedProjects()
        setPmProjectsData(data)
        if (data.projects && data.projects.length > 0) {
          setSelectedPmCase(data.projects[0])
        }
      } else if (activeRole === 'auditor') {
        const data = await api.rbac.auditor.getAssignedProjects()
        setAuditorProjectsData(data)
        if (data.projects && data.projects.length > 0) {
          fetchAuditPack(data.projects[0].case_id)
        }
      }
    } catch (err) {
      console.error('Failed to load role dashboard data:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // --- CSR Head User Management Actions ---
  const fetchUsersList = async () => {
    try {
      const data = await api.rbac.head.getUsers()
      setUsersList(data.users || [])
    } catch (err) {
      console.error('Failed to fetch users list:', err)
    }
  }

  const handleCreateUser = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      await api.rbac.head.createUser({
        user_id: newUser.user_id || `user_${Date.now().toString().slice(-4)}`,
        name: newUser.name,
        email: newUser.email,
        role: newUser.role,
      })
      setSuccess(`User '${newUser.name}' added with role '${newUser.role}'!`)
      setNewUser({ user_id: '', name: '', email: '', role: 'project_manager' })
      fetchUsersList()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleUpdateUserRole = async (userId, newRole) => {
    setError('')
    setSuccess('')
    try {
      await api.rbac.head.updateUserRole(userId, newRole)
      setSuccess(`Role for user '${userId}' updated to '${newRole}'!`)
      fetchUsersList()
    } catch (err) {
      setError(err.message)
    }
  }

  // --- CSR Head Project Actions ---
  const handleCreateProject = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      await api.rbac.head.createProject({
        case_id: newProject.case_id || `CSR-${Date.now().toString().slice(-4)}`,
        title: newProject.title,
        total_budget: parseFloat(newProject.total_budget) || 0,
        assigned_pm_id: newProject.assigned_pm_id,
        assigned_auditor_id: newProject.assigned_auditor_id,
      })
      setSuccess(`Project '${newProject.title}' created successfully by CSR Head!`)
      setShowCreateModal(false)
      setNewProject({ case_id: '', title: '', total_budget: '', assigned_pm_id: 'pm_exec_101', assigned_auditor_id: 'auditor_rev_201' })
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleUpdateProjectSubmit = async (e) => {
    e.preventDefault()
    if (!editingProject) return
    setError('')
    setSuccess('')
    try {
      await api.rbac.head.updateProject(editingProject.case_id, {
        title: editingProject.title,
        total_budget: parseFloat(editingProject.total_budget) || 0,
        assigned_pm_id: editingProject.assigned_pm_id,
        assigned_auditor_id: editingProject.assigned_auditor_id,
      })
      setSuccess(`Project '${editingProject.case_id}' updated successfully!`)
      setShowEditModal(false)
      setEditingProject(null)
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleReopenProject = async (caseId) => {
    setError('')
    setSuccess('')
    try {
      await api.rbac.head.reopenProject(caseId)
      setSuccess(`Project '${caseId}' reopened back to Draft by CSR Head!`)
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleCloseProject = async (caseId) => {
    setError('')
    setSuccess('')
    try {
      await api.rbac.head.closeProject(caseId)
      setSuccess(`Project '${caseId}' marked CLOSED by CSR Head!`)
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleResetAllData = async () => {
    if (!window.confirm('Are you sure you want to wipe all previous documents, projects, and milestones to start a clean fresh demo?')) return
    setError('')
    setSuccess('')
    try {
      await api.rbac.head.resetAllData()
      setSuccess('All system documents, projects, milestones, and KG data cleared successfully for fresh demo!')
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleAdminOverrideSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      await api.rbac.head.overrideProject(overrideData.case_id, overrideData.target_stage, overrideData.comments)
      setSuccess(`Admin override executed for '${overrideData.case_id}' (Set to ${overrideData.target_stage})!`)
      setShowOverrideModal(false)
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  // --- PM Execution Actions ---
  const handlePMMilestoneSubmit = async (e) => {
    e.preventDefault()
    if (!selectedPmCase) return
    setError('')
    setSuccess('')
    try {
      await api.rbac.pm.updateMilestone(selectedPmCase.case_id, {
        title: newMilestone.title,
        target_date: newMilestone.target_date || new Date().toISOString().slice(0, 10),
        allocated_budget: parseFloat(newMilestone.allocated_budget) || 0,
        progress_percentage: parseFloat(newMilestone.progress_percentage) || 0,
        spent_amount: parseFloat(newMilestone.spent_amount) || 0,
      })
      setSuccess(`Milestone '${newMilestone.title}' updated successfully for project ${selectedPmCase.case_id}!`)
      setNewMilestone({ title: '', target_date: '', allocated_budget: '', progress_percentage: 0, spent_amount: 0 })
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handlePMUploadDocSubmit = async (e) => {
    e.preventDefault()
    if (!selectedPmCase) return
    setError('')
    setSuccess('')
    setIsUploadingDoc(true)
    try {
      let docId = `DOC-PM-${Date.now().toString().slice(-4)}`
      let uploadedFilename = pmExecDoc.filename || (pmSelectedFile ? pmSelectedFile.name : 'execution_report.pdf')
      let docType = pmExecDoc.document_type || 'progress_report'
      let rawText = pmExecDoc.raw_text || ''

      if (pmSelectedFile) {
        const uploadRes = await api.upload(pmSelectedFile)
        if (uploadRes && uploadRes.document_id) {
          docId = uploadRes.document_id
          uploadedFilename = pmSelectedFile.name
          if (uploadRes.document_type) {
            docType = uploadRes.document_type
          }
          if (uploadRes.extracted_fields) {
            rawText = rawText || JSON.stringify(uploadRes.extracted_fields)
          }
        }
      }

      await api.rbac.pm.uploadDocument(selectedPmCase.case_id, {
        document_id: docId,
        filename: uploadedFilename,
        document_type: docType,
        raw_text: rawText,
      })

      setSuccess(`Execution document '${uploadedFilename}' uploaded & attached to project ${selectedPmCase.case_id}!`)
      setPmExecDoc({ filename: '', document_type: 'progress_report', raw_text: '' })
      setPmSelectedFile(null)
      loadRoleData()
    } catch (err) {
      setError(err.message || 'Failed to attach execution document.')
    } finally {
      setIsUploadingDoc(false)
    }
  }

  const handlePMSubmitProject = async (caseId) => {
    setError('')
    setSuccess('')
    try {
      await api.rbac.pm.submitProject(caseId)
      setSuccess(`Project ${caseId} proposal submitted for audit review!`)
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handlePMStageChange = async (caseId, targetStage) => {
    setError('')
    setSuccess('')
    try {
      await api.rbac.pm.updateStage(caseId, targetStage)
      setSuccess(`Project ${caseId} stage moved to ${targetStage}!`)
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  // --- Auditor Actions ---
  const [auditorDocNotes, setAuditorDocNotes] = useState({})

  const fetchAuditPack = async (caseId) => {
    try {
      const pack = await api.rbac.auditor.getAuditPack(caseId)
      setSelectedAuditPack(pack)
    } catch (err) {
      console.error('Failed to fetch audit pack:', err)
    }
  }

  const handleAuditorVerifyDoc = async (documentId, status) => {
    if (!selectedAuditPack) return
    setError('')
    setSuccess('')
    try {
      const notes = auditorDocNotes[documentId] || ''
      const res = await api.rbac.auditor.verifyDocument(selectedAuditPack.case_id, documentId, status, notes)
      setSuccess(res.message || `Document '${documentId}' verification set to ${status.toUpperCase()}!`)
      fetchAuditPack(selectedAuditPack.case_id)
      loadRoleData()
    } catch (err) {
      setError(err.message || 'Failed to update document status.')
    }
  }

  const handleAuditorDecisionSubmit = async (e) => {
    e.preventDefault()
    if (!selectedAuditPack) return
    setError('')
    setSuccess('')
    try {
      await api.rbac.auditor.submitDecision(
        selectedAuditPack.case_id,
        auditDecision.action,
        auditDecision.comments || 'Audit verification completed.'
      )
      setSuccess(`Auditor decision '${auditDecision.action}' submitted for project ${selectedAuditPack.case_id}!`)
      setAuditDecision({ action: 'APPROVE', comments: '' })
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleAuditorMarkComplete = async (caseId) => {
    setError('')
    setSuccess('')
    try {
      await api.rbac.auditor.markComplete(caseId)
      setSuccess(`Project ${caseId} verified and marked completed!`)
      loadRoleData()
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-primary-700 via-primary-800 to-gray-900 text-white rounded-2xl p-6 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 bg-white/10 px-3 py-1 rounded-full text-xs font-semibold mb-2">
              <span>{roleConfig.badge}</span>
              <span>•</span>
              <span>{roleConfig.email}</span>
            </div>
            <h1 className="text-2xl font-bold">{roleConfig.name} Control Dashboard</h1>
            <p className="text-primary-100 text-sm mt-1">
              {activeRole === 'csr_head' && 'Manage programme-wide CSR projects, allocate budgets, assign teams, manage users & view aggregate analytics.'}
              {activeRole === 'project_manager' && 'Execute assigned CSR projects, upload progress reports, track milestones & submit proposals.'}
              {activeRole === 'auditor' && 'Independent review dashboard for statutory compliance verification, audit pack inspection & approval decisions.'}
            </p>
          </div>
        </div>
      </div>

      {/* Global Alerts */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-xl flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm font-medium">{error}</div>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-800 p-4 rounded-xl flex items-start space-x-3">
          <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm font-medium">{success}</div>
        </div>
      )}

      {/* =================================================================== */}
      {/* 1. CSR HEAD (ADMIN) DASHBOARD VIEW */}
      {/* =================================================================== */}
      {activeRole === 'csr_head' && (
        <div className="space-y-6">
          {/* Stats Widgets */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 uppercase">Total CSR Projects</span>
                <Building2 className="w-5 h-5 text-primary-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900 mt-2">{headProjectsData?.total_projects || 0}</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 uppercase">Programme Budget</span>
                <DollarSign className="w-5 h-5 text-green-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                ₹{(headProjectsData?.total_program_budget || 0).toLocaleString()}
              </p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 uppercase">Programme Spent</span>
                <TrendingUp className="w-5 h-5 text-blue-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                ₹{(headProjectsData?.total_program_spent || 0).toLocaleString()}
              </p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 uppercase">Role Access</span>
                <Shield className="w-5 h-5 text-purple-600" />
              </div>
              <p className="text-base font-bold text-purple-700 mt-2">CSR Head (Admin)</p>
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-4 rounded-xl border border-gray-200 shadow-sm gap-3">
            <div>
              <h2 className="text-lg font-bold text-gray-900">CSR Programme Projects & Governance</h2>
              <p className="text-xs text-gray-500">Full programme control: Create projects, manage users, assign teams & lifecycle stage overrides</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleResetAllData}
                className="inline-flex items-center space-x-1.5 bg-red-50 hover:bg-red-100 text-red-700 text-xs font-semibold px-3 py-2 rounded-xl transition-colors border border-red-200"
                title="Wipe all previous data for fresh demo"
              >
                <RotateCcw className="w-3.5 h-3.5 text-red-600" />
                <span>Reset All Data</span>
              </button>
              <button
                onClick={() => { fetchUsersList(); setShowUserModal(true); }}
                className="inline-flex items-center space-x-1.5 bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold px-3 py-2 rounded-xl transition-colors"
              >
                <Users className="w-4 h-4 text-purple-600" />
                <span>Manage Team Users</span>
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center space-x-1.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-sm"
              >
                <FolderPlus className="w-4 h-4" />
                <span>Create New Project</span>
              </button>
            </div>
          </div>

          {/* Projects Table */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3">Case ID</th>
                  <th className="px-6 py-3">Project Title</th>
                  <th className="px-6 py-3">Current Stage</th>
                  <th className="px-6 py-3">Budget / Spent</th>
                  <th className="px-6 py-3">Assigned PM</th>
                  <th className="px-6 py-3">Assigned Auditor</th>
                  <th className="px-6 py-3">Progress</th>
                  <th className="px-6 py-3 text-right">Admin Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 font-medium text-gray-800">
                {headProjectsData?.projects?.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="px-6 py-8 text-center text-gray-400">
                      No CSR projects created yet. Click "Create New Project" above or upload CSR documents.
                    </td>
                  </tr>
                ) : (
                  headProjectsData?.projects?.map((proj) => (
                    <tr key={proj.case_id} className="hover:bg-gray-50/80">
                      <td className="px-6 py-4 font-bold text-primary-700">{proj.case_id}</td>
                      <td className="px-6 py-4 max-w-[200px] truncate">{proj.title}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${
                          proj.current_stage === 'APPROVED' || proj.current_stage === 'VERIFIED_COMPLETED' ? 'bg-green-100 text-green-800' :
                          proj.current_stage === 'REJECTED' ? 'bg-red-100 text-red-800' :
                          proj.current_stage === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {proj.current_stage || 'DRAFT'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs font-medium">
                        <div className="text-gray-900 font-bold">₹{(proj.total_budget || 0).toLocaleString()}</div>
                        <div className="text-gray-500 text-[11px]">Spent: ₹{(proj.total_spent || 0).toLocaleString()}</div>
                      </td>
                      <td className="px-6 py-4 text-xs font-mono text-gray-600">{proj.assigned_pm_id}</td>
                      <td className="px-6 py-4 text-xs font-mono text-gray-600">{proj.assigned_auditor_id}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-2">
                          <div className="w-20 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-primary-600 h-2 rounded-full"
                              style={{ width: `${proj.milestone_summary?.overall_progress_percentage || 0}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-600 font-semibold">
                            {proj.milestone_summary?.overall_progress_percentage || 0}%
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right space-x-1">
                        <button
                          onClick={() => { setEditingProject(proj); setShowEditModal(true); }}
                          title="Edit core details and baseline budget"
                          className="px-2 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs rounded font-medium inline-flex items-center space-x-1"
                        >
                          <Edit3 className="w-3 h-3" />
                          <span>Edit</span>
                        </button>

                        {proj.current_stage === 'REJECTED' && (
                          <button
                            onClick={() => handleReopenProject(proj.case_id)}
                            title="Reopen rejected project back to Draft"
                            className="px-2 py-1 bg-amber-100 hover:bg-amber-200 text-amber-800 text-xs rounded font-medium inline-flex items-center space-x-1"
                          >
                            <RotateCcw className="w-3 h-3" />
                            <span>Reopen</span>
                          </button>
                        )}

                        <button
                          onClick={() => { setOverrideData({ case_id: proj.case_id, target_stage: 'IN_PROGRESS', comments: '' }); setShowOverrideModal(true); }}
                          title="Admin override workflow stage"
                          className="px-2 py-1 bg-purple-100 hover:bg-purple-200 text-purple-800 text-xs rounded font-medium inline-flex items-center space-x-1"
                        >
                          <Sliders className="w-3 h-3" />
                          <span>Override</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* User Management Modal */}
          {showUserModal && (
            <div className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white max-w-2xl w-full rounded-2xl p-6 shadow-xl space-y-6">
                <div className="flex justify-between items-center border-b pb-3">
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 flex items-center space-x-2">
                      <Users className="w-5 h-5 text-purple-600" />
                      <span>Manage Team Members & Role Access</span>
                    </h3>
                    <p className="text-xs text-gray-500">Create team users and assign role permissions (`CSR Head`, `Project Manager`, `Auditor`)</p>
                  </div>
                  <button onClick={() => setShowUserModal(false)} className="text-gray-400 hover:text-gray-600 text-lg">✕</button>
                </div>

                {/* Users List */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500">Registered Team Users ({usersList.length})</h4>
                  <div className="max-h-56 overflow-y-auto space-y-2 border rounded-xl p-2 bg-gray-50/50">
                    {usersList.map((u) => (
                      <div key={u.user_id} className="flex items-center justify-between p-2.5 bg-white border rounded-lg shadow-sm text-xs">
                        <div>
                          <div className="font-bold text-gray-900">{u.name} <span className="font-normal text-gray-500">({u.user_id})</span></div>
                          <div className="text-gray-500 text-[11px]">{u.email}</div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <select
                            value={u.role}
                            onChange={(e) => handleUpdateUserRole(u.user_id, e.target.value)}
                            className="text-xs font-semibold border rounded-lg p-1.5 bg-gray-50 focus:ring-2 focus:ring-purple-500"
                          >
                            <option value="csr_head">👑 CSR Head (Admin)</option>
                            <option value="project_manager">⚡ Project Manager (Execution)</option>
                            <option value="auditor">🔍 Approver / Auditor (Reviewer)</option>
                          </select>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Add New User Form */}
                <form onSubmit={handleCreateUser} className="border-t pt-4 space-y-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center space-x-1.5">
                    <UserPlus className="w-4 h-4 text-primary-600" />
                    <span>Add New Team User</span>
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">User ID</label>
                      <input
                        type="text"
                        placeholder="e.g. pm_exec_103"
                        value={newUser.user_id}
                        onChange={(e) => setNewUser({ ...newUser, user_id: e.target.value })}
                        className="w-full text-xs border rounded-lg p-2"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Full Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Anjali Sharma"
                        value={newUser.name}
                        onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                        className="w-full text-xs border rounded-lg p-2"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Email</label>
                      <input
                        type="email"
                        placeholder="e.g. anjali@csrflow.com"
                        value={newUser.email}
                        onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                        className="w-full text-xs border rounded-lg p-2"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Assigned Role</label>
                      <select
                        value={newUser.role}
                        onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                        className="w-full text-xs border rounded-lg p-2"
                      >
                        <option value="project_manager">⚡ Project Manager (Execution)</option>
                        <option value="auditor">🔍 Approver / Auditor (Reviewer)</option>
                        <option value="csr_head">👑 CSR Head (Admin)</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex justify-end space-x-2 pt-2 border-t">
                    <button
                      type="button"
                      onClick={() => setShowUserModal(false)}
                      className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg"
                    >
                      Close
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 text-xs font-semibold bg-purple-700 hover:bg-purple-800 text-white rounded-lg shadow-sm"
                    >
                      Register User
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Edit Project Details Modal */}
          {showEditModal && editingProject && (
            <div className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white max-w-md w-full rounded-2xl p-6 shadow-xl space-y-4">
                <div className="flex justify-between items-center border-b pb-3">
                  <h3 className="text-lg font-bold text-gray-900">Edit Project Details</h3>
                  <button onClick={() => setShowEditModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
                </div>
                <form onSubmit={handleUpdateProjectSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Case ID (Read Only)</label>
                    <input
                      type="text"
                      value={editingProject.case_id}
                      disabled
                      className="w-full text-xs border rounded-lg p-2 bg-gray-100 text-gray-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Project Title</label>
                    <input
                      type="text"
                      value={editingProject.title}
                      onChange={(e) => setEditingProject({ ...editingProject, title: e.target.value })}
                      className="w-full text-xs border rounded-lg p-2 focus:ring-2 focus:ring-primary-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Total Baseline Budget (₹)</label>
                    <input
                      type="number"
                      value={editingProject.total_budget}
                      onChange={(e) => setEditingProject({ ...editingProject, total_budget: e.target.value })}
                      className="w-full text-xs border rounded-lg p-2 focus:ring-2 focus:ring-primary-500"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Reassign PM</label>
                      <select
                        value={editingProject.assigned_pm_id}
                        onChange={(e) => setEditingProject({ ...editingProject, assigned_pm_id: e.target.value })}
                        className="w-full text-xs border rounded-lg p-2"
                      >
                        <option value="pm_exec_101">PM Exec 101</option>
                        <option value="pm_exec_102">PM Exec 102</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Reassign Auditor</label>
                      <select
                        value={editingProject.assigned_auditor_id}
                        onChange={(e) => setEditingProject({ ...editingProject, assigned_auditor_id: e.target.value })}
                        className="w-full text-xs border rounded-lg p-2"
                      >
                        <option value="auditor_rev_201">Auditor 201</option>
                        <option value="auditor_rev_202">Auditor 202</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex justify-end space-x-2 pt-2 border-t">
                    <button
                      type="button"
                      onClick={() => setShowEditModal(false)}
                      className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 text-xs font-semibold bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                      Save Changes
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Admin Override Modal */}
          {showOverrideModal && (
            <div className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white max-w-md w-full rounded-2xl p-6 shadow-xl space-y-4">
                <div className="flex justify-between items-center border-b pb-3">
                  <h3 className="text-lg font-bold text-gray-900 flex items-center space-x-2">
                    <Sliders className="w-5 h-5 text-purple-600" />
                    <span>Admin Stage Override</span>
                  </h3>
                  <button onClick={() => setShowOverrideModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
                </div>
                <form onSubmit={handleAdminOverrideSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Target Stage</label>
                    <select
                      value={overrideData.target_stage}
                      onChange={(e) => setOverrideData({ ...overrideData, target_stage: e.target.value })}
                      className="w-full text-xs border rounded-lg p-2"
                    >
                      <option value="IN_PROGRESS">IN_PROGRESS</option>
                      <option value="MONITORING">MONITORING</option>
                      <option value="DRAFT">DRAFT</option>
                      <option value="SUBMITTED">SUBMITTED</option>
                      <option value="APPROVED">APPROVED</option>
                      <option value="CLOSED">CLOSED</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Override Rationale / Audit Note</label>
                    <textarea
                      rows="3"
                      placeholder="Reason for admin override..."
                      value={overrideData.comments}
                      onChange={(e) => setOverrideData({ ...overrideData, comments: e.target.value })}
                      className="w-full text-xs border rounded-lg p-2"
                      required
                    />
                  </div>
                  <div className="flex justify-end space-x-2 pt-2 border-t">
                    <button
                      type="button"
                      onClick={() => setShowOverrideModal(false)}
                      className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 text-xs font-semibold bg-purple-700 hover:bg-purple-800 text-white rounded-lg shadow-sm"
                    >
                      Execute Override
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Create Project Modal */}
          {showCreateModal && (
            <div className="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white max-w-md w-full rounded-2xl p-6 shadow-xl space-y-4">
                <div className="flex justify-between items-center border-b pb-3">
                  <h3 className="text-lg font-bold text-gray-900">Create New CSR Project</h3>
                  <button onClick={() => setShowCreateModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
                </div>
                <form onSubmit={handleCreateProject} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Case ID</label>
                    <input
                      type="text"
                      placeholder="e.g. CSR-SOLAR-2026"
                      value={newProject.case_id}
                      onChange={(e) => setNewProject({ ...newProject, case_id: e.target.value })}
                      className="w-full text-sm border rounded-lg p-2.5 focus:ring-2 focus:ring-primary-500 focus:outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Project Title</label>
                    <input
                      type="text"
                      placeholder="e.g. Rural Solar & School Renovation Project"
                      value={newProject.title}
                      onChange={(e) => setNewProject({ ...newProject, title: e.target.value })}
                      className="w-full text-sm border rounded-lg p-2.5 focus:ring-2 focus:ring-primary-500 focus:outline-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">Total Allocated Budget (₹)</label>
                    <input
                      type="number"
                      placeholder="5000000"
                      value={newProject.total_budget}
                      onChange={(e) => setNewProject({ ...newProject, total_budget: e.target.value })}
                      className="w-full text-sm border rounded-lg p-2.5 focus:ring-2 focus:ring-primary-500 focus:outline-none"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Assign PM</label>
                      <select
                        value={newProject.assigned_pm_id}
                        onChange={(e) => setNewProject({ ...newProject, assigned_pm_id: e.target.value })}
                        className="w-full text-xs border rounded-lg p-2"
                      >
                        <option value="pm_exec_101">PM Exec 101</option>
                        <option value="pm_exec_102">PM Exec 102</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Assign Auditor</label>
                      <select
                        value={newProject.assigned_auditor_id}
                        onChange={(e) => setNewProject({ ...newProject, assigned_auditor_id: e.target.value })}
                        className="w-full text-xs border rounded-lg p-2"
                      >
                        <option value="auditor_rev_201">Auditor 201</option>
                        <option value="auditor_rev_202">Auditor 202</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex justify-end space-x-2 pt-2 border-t">
                    <button
                      type="button"
                      onClick={() => setShowCreateModal(false)}
                      className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 text-xs font-semibold bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                      Save Project
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* 2. PROJECT MANAGER (EXECUTION) DASHBOARD VIEW */}
      {/* =================================================================== */}
      {activeRole === 'project_manager' && (
        <div className="space-y-6">
          {/* PM Notice */}
          <div className="bg-amber-50 border border-amber-200 text-amber-900 p-4 rounded-xl text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="w-4 h-4 text-amber-600" />
              <span><strong>Execution Scoped Access:</strong> You are viewing projects assigned to you (`pm_exec_101`). Project Creation, Auditor Approvals, and Team Role Assignments are restricted.</span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Assigned Projects List */}
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
              <h2 className="text-base font-bold text-gray-900 border-b pb-2">My Assigned Execution Projects</h2>
              <div className="space-y-2">
                {pmProjectsData?.projects?.length === 0 ? (
                  <p className="text-xs text-gray-400 py-4">No execution projects assigned to you yet.</p>
                ) : (
                  pmProjectsData?.projects?.map((proj) => (
                    <div
                      key={proj.case_id}
                      onClick={() => setSelectedPmCase(proj)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedPmCase?.case_id === proj.case_id
                          ? 'border-primary-600 bg-primary-50/50 shadow-sm'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-bold text-primary-700">{proj.case_id}</span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 bg-gray-100 rounded-full text-gray-700">
                          {proj.current_stage}
                        </span>
                      </div>
                      <p className="text-sm font-semibold text-gray-800 mt-1">{proj.title}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* PM Execution Details & Milestone Tracker */}
            <div className="lg:col-span-2 space-y-6">
              {selectedPmCase ? (
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-6">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b pb-4">
                    <div>
                      <span className="text-xs font-bold text-primary-600">{selectedPmCase.case_id}</span>
                      <h2 className="text-xl font-bold text-gray-900">{selectedPmCase.title}</h2>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handlePMStageChange(selectedPmCase.case_id, 'IN_PROGRESS')}
                        className="bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold px-2.5 py-1.5 rounded-lg"
                      >
                        Set In Progress
                      </button>
                      <button
                        onClick={() => handlePMStageChange(selectedPmCase.case_id, 'MONITORING')}
                        className="bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold px-2.5 py-1.5 rounded-lg"
                      >
                        Set Monitoring
                      </button>
                      <button
                        onClick={() => handlePMSubmitProject(selectedPmCase.case_id)}
                        className="inline-flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3 py-2 rounded-lg shadow-sm"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Submit for Audit Review</span>
                      </button>
                    </div>
                  </div>


                  {/* Milestone Progress Form */}
                  <form onSubmit={handlePMMilestoneSubmit} className="bg-gray-50 p-4 rounded-xl border border-gray-200 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-gray-900">Add / Update Execution Milestone</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Milestone Title</label>
                        <input
                          type="text"
                          placeholder="e.g. Phase 1: Equipment Procurement"
                          value={newMilestone.title}
                          onChange={(e) => setNewMilestone({ ...newMilestone, title: e.target.value })}
                          className="w-full text-xs border rounded-lg p-2"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Target Date</label>
                        <input
                          type="date"
                          value={newMilestone.target_date}
                          onChange={(e) => setNewMilestone({ ...newMilestone, target_date: e.target.value })}
                          className="w-full text-xs border rounded-lg p-2"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Allocated Budget (₹)</label>
                        <input
                          type="number"
                          placeholder="1000000"
                          value={newMilestone.allocated_budget}
                          onChange={(e) => setNewMilestone({ ...newMilestone, allocated_budget: e.target.value })}
                          className="w-full text-xs border rounded-lg p-2"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Spent Amount (₹)</label>
                        <input
                          type="number"
                          placeholder="750000"
                          value={newMilestone.spent_amount}
                          onChange={(e) => setNewMilestone({ ...newMilestone, spent_amount: e.target.value })}
                          className="w-full text-xs border rounded-lg p-2"
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs font-semibold text-gray-700 mb-1">
                        <span>Progress Percentage</span>
                        <span>{newMilestone.progress_percentage}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={newMilestone.progress_percentage}
                        onChange={(e) => setNewMilestone({ ...newMilestone, progress_percentage: e.target.value })}
                        className="w-full accent-primary-600"
                      />
                    </div>
                    <button
                      type="submit"
                      className="bg-primary-600 hover:bg-primary-700 text-white text-xs font-semibold px-4 py-2 rounded-lg"
                    >
                      Save Milestone Progress
                    </button>
                  </form>

                  {/* ATTACH EXECUTION DOCUMENT / EVIDENCE CARD */}
                  <form onSubmit={handlePMUploadDocSubmit} className="bg-blue-50/50 p-5 rounded-xl border border-blue-100 space-y-4">
                    <div className="flex items-center space-x-2 text-blue-900 font-bold text-xs uppercase tracking-wider">
                      <Upload className="w-4 h-4 text-blue-600" />
                      <span>ATTACH EXECUTION DOCUMENT / EVIDENCE</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Filename</label>
                        <div className="space-y-2">
                          <input
                            type="text"
                            placeholder="e.g. q3_expense_invoice.pdf"
                            value={pmExecDoc.filename}
                            onChange={(e) => setPmExecDoc({ ...pmExecDoc, filename: e.target.value })}
                            className="w-full text-xs border border-gray-200 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                          />
                          <div className="flex items-center space-x-2">
                            <label className="cursor-pointer inline-flex items-center space-x-1.5 bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm">
                              <Upload className="w-3.5 h-3.5 text-blue-600" />
                              <span>{pmSelectedFile ? 'Change Local File' : 'Choose Local File'}</span>
                              <input
                                type="file"
                                onChange={(e) => {
                                  const file = e.target.files[0]
                                  if (file) {
                                    setPmSelectedFile(file)
                                    setPmExecDoc(prev => ({ ...prev, filename: file.name }))
                                  }
                                }}
                                className="hidden"
                              />
                            </label>
                            {pmSelectedFile && (
                              <span className="text-[11px] text-gray-600 bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-medium truncate max-w-[180px]">
                                {pmSelectedFile.name} ({(pmSelectedFile.size / 1024).toFixed(0)} KB)
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">Document Category</label>
                        <select
                          value={pmExecDoc.document_type}
                          onChange={(e) => setPmExecDoc({ ...pmExecDoc, document_type: e.target.value })}
                          className="w-full text-xs border border-gray-200 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                        >
                          <option value="progress_report">Progress Report</option>
                          <option value="expense_report">Expense Report</option>
                          <option value="invoice">Bills / Invoices</option>
                          <option value="beneficiary_report">Beneficiary Report</option>
                          <option value="evidence">Photos / Evidence</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">Notes / Summary</label>
                      <input
                        type="text"
                        placeholder="Key highlights from report..."
                        value={pmExecDoc.raw_text}
                        onChange={(e) => setPmExecDoc({ ...pmExecDoc, raw_text: e.target.value })}
                        className="w-full text-xs border border-gray-200 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                    </div>

                    <div>
                      <button
                        type="submit"
                        disabled={isUploadingDoc}
                        className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold text-xs px-5 py-2.5 rounded-lg shadow-sm transition-colors inline-flex items-center space-x-2"
                      >
                        {isUploadingDoc ? (
                          <>
                            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            <span>Uploading & Processing...</span>
                          </>
                        ) : (
                          <span>Attach Execution Document</span>
                        )}
                      </button>
                    </div>
                  </form>
                </div>
              ) : (
                <div className="bg-white p-8 text-center text-gray-400 rounded-xl border">
                  Select a project from the left to manage execution.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* 3. APPROVER / AUDITOR (INDEPENDENT REVIEWER) DASHBOARD VIEW */}
      {/* =================================================================== */}
      {activeRole === 'auditor' && (
        <div className="space-y-6">
          {/* Auditor Notice */}
          <div className="bg-purple-50 border border-purple-200 text-purple-900 p-4 rounded-xl text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="w-4 h-4 text-purple-600" />
              <span><strong>Independent Document Audit Center:</strong> You are auditing execution evidence documents (invoices, reports, bills) for assigned project case `auditor_rev_201`. As Auditor, you review and verify, hold, or reject individual documents. Overall project creation & stage lifecycle belong to CSR Head & PM.</span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Assigned Review Projects */}
            <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
              <h2 className="text-base font-bold text-gray-900 border-b pb-2">Assigned Audit Reviews</h2>
              <div className="space-y-2">
                {auditorProjectsData?.projects?.map((proj) => (
                  <div
                    key={proj.case_id}
                    onClick={() => fetchAuditPack(proj.case_id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      selectedAuditPack?.case_id === proj.case_id
                        ? 'border-purple-600 bg-purple-50/50 shadow-sm'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-bold text-purple-700">{proj.case_id}</span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 bg-purple-100 text-purple-800 rounded-full">
                        {proj.current_stage}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-gray-800 mt-1">{proj.title}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Audit Control Pack Inspector */}
            <div className="lg:col-span-2 space-y-6">
              {selectedAuditPack ? (
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-6">
                  <div className="flex justify-between items-center border-b pb-4">
                    <div>
                      <span className="text-xs font-bold text-purple-600">{selectedAuditPack.case_id}</span>
                      <h2 className="text-xl font-bold text-gray-900">{selectedAuditPack.project_title}</h2>
                    </div>
                    <span className="text-xs font-semibold px-3 py-1.5 bg-purple-100 text-purple-800 rounded-lg">
                      Audit Case: {selectedAuditPack.documents?.length || 0} Documents
                    </span>
                  </div>

                  {/* Statutory Compliance & AI Flags Card */}
                  <div className="bg-purple-50/50 p-4 rounded-xl border border-purple-100 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-bold text-purple-800">Statutory Compliance Score</span>
                      <span className="text-base font-bold text-purple-900">
                        {selectedAuditPack.statutory_compliance_report?.compliance_score || 100}%
                      </span>
                    </div>
                    <div className="flex space-x-2">
                      <span className="px-2 py-0.5 text-xs font-bold bg-green-100 text-green-800 rounded">
                        {selectedAuditPack.statutory_compliance_report?.status || 'FULLY_COMPLIANT'}
                      </span>
                      <span className="px-2 py-0.5 text-xs font-bold bg-blue-100 text-blue-800 rounded">
                        Risk: {selectedAuditPack.statutory_compliance_report?.risk_level || 'LOW'}
                      </span>
                    </div>
                  </div>

                  {/* Document Audit & Verification Panel */}
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider border-b pb-2">
                      Audit & Verify Project Execution Documents
                    </h3>

                    {(!selectedAuditPack.documents || selectedAuditPack.documents.length === 0) ? (
                      <div className="p-4 bg-gray-50 border rounded-xl text-center text-xs text-gray-500">
                        No execution documents uploaded for this project yet. PM needs to attach reports/invoices.
                      </div>
                    ) : (
                      selectedAuditPack.documents.map((doc) => (
                        <div key={doc.document_id} className="bg-gray-50 p-4 rounded-xl border border-gray-200 space-y-3">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-200 pb-2">
                            <div>
                              <span className="text-xs font-bold text-purple-700 font-mono">{doc.document_id}</span>
                              <h4 className="text-sm font-bold text-gray-900">{doc.filename || doc.document_id}</h4>
                              <p className="text-[11px] text-gray-500">Category: <span className="font-semibold text-gray-700">{doc.document_type || 'General'}</span></p>
                            </div>
                            <div>
                              {(!doc.verification_status || doc.verification_status === 'unverified') && (
                                <span className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-bold bg-gray-200 text-gray-800 rounded-full">
                                  <Clock className="w-3 h-3" />
                                  <span>Unreviewed</span>
                                </span>
                              )}
                              {(doc.verification_status === 'hold' || doc.verification_status === 'needs_review') && (
                                <span className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-bold bg-amber-100 text-amber-800 rounded-full">
                                  <Clock className="w-3 h-3" />
                                  <span>Hold for Review</span>
                                </span>
                              )}
                              {doc.verification_status === 'verified' && (
                                <span className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-bold bg-green-100 text-green-800 rounded-full">
                                  <CheckCircle className="w-3 h-3" />
                                  <span>Verified / Approved</span>
                                </span>
                              )}
                              {doc.verification_status === 'rejected' && (
                                <span className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-bold bg-red-100 text-red-800 rounded-full">
                                  <XCircle className="w-3 h-3" />
                                  <span>Rejected</span>
                                </span>
                              )}
                            </div>
                          </div>

                          <div>
                            <label className="block text-[11px] font-semibold text-gray-600 mb-1">Auditor Verification Notes</label>
                            <input
                              type="text"
                              placeholder="Auditor rationale and verification notes for this document..."
                              value={auditorDocNotes[doc.document_id] !== undefined ? auditorDocNotes[doc.document_id] : (doc.verification_reason || '')}
                              onChange={(e) => setAuditorDocNotes({ ...auditorDocNotes, [doc.document_id]: e.target.value })}
                              className="w-full text-xs border border-gray-300 rounded-lg p-2 bg-white outline-none focus:ring-2 focus:ring-purple-500"
                            />
                          </div>

                          <div className="flex flex-wrap gap-2 pt-1">
                            <button
                              type="button"
                              onClick={() => handleAuditorVerifyDoc(doc.document_id, 'verified')}
                              className="inline-flex items-center space-x-1 bg-green-600 hover:bg-green-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm transition-colors"
                            >
                              <CheckCircle className="w-3.5 h-3.5" />
                              <span>Approve Document</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleAuditorVerifyDoc(doc.document_id, 'needs_review')}
                              className="inline-flex items-center space-x-1 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm transition-colors"
                            >
                              <Clock className="w-3.5 h-3.5" />
                              <span>Hold for Review</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleAuditorVerifyDoc(doc.document_id, 'rejected')}
                              className="inline-flex items-center space-x-1 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm transition-colors"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              <span>Reject Document</span>
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : (
                <div className="bg-white p-8 text-center text-gray-400 rounded-xl border">
                  Select a review project from the left to inspect audit pack.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
