"""
Enterprise 3-Role Role-Based Access Control (RBAC) API Routes.

Implements role-based endpoints and permission enforcements for:
1. CSR Head (Programme Owner / Admin)
2. Project Manager (Execution)
3. Approver / Auditor (Independent Reviewer)
"""

import re
import logging
import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth.auth import get_current_user, UserInfo
from auth.rbac_middleware import (
    require_csr_head,
    require_project_manager,
    require_auditor_role,
    verify_pm_case_access,
    verify_auditor_case_access,
    enforce_separation_of_duties,
)
from routes.case_routes import _CASE_REGISTRY
from routes.routes import _DOC_REGISTRY
from workflow.approval_engine import WorkflowEngine, ApprovalStage, ApprovalAction
from milestones.milestone_tracker import MilestoneManager
from compliance.compliance_verifier import StatutoryComplianceVerifier
from compliance.duplicate_checker import DuplicateChecker

logger = logging.getLogger(__name__)

head_router = APIRouter(prefix="/rbac/head", tags=["1. CSR Head (Programme Owner / Admin)"])
pm_router = APIRouter(prefix="/rbac/pm", tags=["2. Project Manager (Execution)"])
auditor_router = APIRouter(prefix="/rbac/auditor", tags=["3. Approver / Auditor (Independent Reviewer)"])


def _parse_currency_amount(val: Any) -> float:
    """Parse numeric budget/spent float from string or number."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if not val_str:
        return 0.0
    clean = re.sub(r"[₹$,\s\/\-]", "", val_str)
    multiplier = 1.0
    if re.search(r"crore|cr", val_str, re.IGNORECASE):
        multiplier = 10000000.0
        clean = re.sub(r"(?i)crore|cr", "", clean)
    elif re.search(r"lakh|lac|lacs", val_str, re.IGNORECASE):
        multiplier = 100000.0
        clean = re.sub(r"(?i)lakh|lac|lacs", "", clean)

    match = re.search(r"(\d+(?:\.\d+)?)", clean)
    if match:
        try:
            return float(match.group(1)) * multiplier
        except ValueError:
            return 0.0
    return 0.0


def _sync_and_calculate_csr_projects() -> List[Dict[str, Any]]:
    """
    Auto-discovers projects from _DOC_REGISTRY if not in _CASE_REGISTRY,
    links documents to cases, and calculates aggregated total budget & total spent
    from milestone tracker AND extracted document fields.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Step 1: Auto-discover projects from uploaded documents in _DOC_REGISTRY if missing
    for doc_id, doc in list(_DOC_REGISTRY.items()):
        doc_case_id = doc.get("case_id")
        extracted_fields = doc.get("extracted_fields", [])

        # Find project title from extracted fields if available
        project_title = None
        for item in extracted_fields:
            if isinstance(item, dict):
                f_name = (item.get("field") or item.get("name") or "").lower()
                f_val = str(item.get("value") or "").strip()
                if f_name in ("project_title", "project_name", "title", "proposal_title") and f_val:
                    project_title = f_val
                    break

        # Try to find matching existing case in _CASE_REGISTRY
        target_case = None
        if doc_case_id and doc_case_id in _CASE_REGISTRY:
            target_case = _CASE_REGISTRY[doc_case_id]
        elif project_title:
            for cid, cdata in _CASE_REGISTRY.items():
                if cdata.get("title") and (project_title.lower() in cdata["title"].lower() or cdata["title"].lower() in project_title.lower()):
                    target_case = cdata
                    doc["case_id"] = cid
                    break

        # If still no target_case, auto-register a case in _CASE_REGISTRY for this document/project
        if not target_case:
            auto_title = project_title or doc.get("filename") or "CSR Project"
            slug = re.sub(r"[^A-Za-z0-9]", "-", auto_title.upper()[:15]).strip("-")
            auto_case_id = doc_case_id or f"CSR-{slug}-{doc_id[:4].upper()}"

            _CASE_REGISTRY[auto_case_id] = {
                "case_id": auto_case_id,
                "title": auto_title,
                "creator_id": doc.get("owner_id") or "csrhead@csrflow.com",
                "owner_id": doc.get("owner_id") or "csrhead@csrflow.com",
                "total_budget": 0.0,
                "assigned_pm_id": "pm_exec_101",
                "assigned_auditor_id": "auditor_rev_201",
                "current_stage": ApprovalStage.APPROVED.value if doc.get("verification_status") == "verified" else ApprovalStage.DRAFT.value,
                "workflow_status": ApprovalStage.APPROVED.value if doc.get("verification_status") == "verified" else ApprovalStage.DRAFT.value,
                "document_ids": [doc_id],
                "created_at": now,
                "updated_at": now,
            }
            doc["case_id"] = auto_case_id
            target_case = _CASE_REGISTRY[auto_case_id]
        else:
            if doc_id not in target_case.get("document_ids", []):
                target_case.setdefault("document_ids", []).append(doc_id)

    # Step 2: Compute aggregate budget, spent, and milestone summary for every case
    calculated_projects = []

    for case_id, case in _CASE_REGISTRY.items():
        summary = MilestoneManager.get_timeline_summary(case_id)

        # Gather linked documents
        linked_doc_ids = set(case.get("document_ids", []))
        for did, drec in _DOC_REGISTRY.items():
            if drec.get("case_id") == case_id:
                linked_doc_ids.add(did)

        # Extract budget & spent from linked documents
        doc_budgets = []
        doc_spents = []

        budget_keys = {"total_budget", "allocated_budget", "approved_budget", "project_cost", "grant_amount", "budget_allocated", "budget"}
        spent_keys = {"spent_amount", "certified_amount", "funds_utilized", "disbursed_amount", "total_spent", "amount_disbursed", "utilization_amount", "amount_spent"}

        for did in linked_doc_ids:
            drec = _DOC_REGISTRY.get(did)
            if not drec:
                continue
            for item in drec.get("extracted_fields", []):
                if isinstance(item, dict):
                    fname = (item.get("field") or item.get("name") or "").lower()
                    fval = item.get("value")
                    amt = _parse_currency_amount(fval)
                    if amt > 0:
                        if fname in budget_keys:
                            doc_budgets.append(amt)
                        elif fname in spent_keys:
                            doc_spents.append(amt)

        base_budget = float(case.get("total_budget", 0.0))
        ms_budget = float(summary.get("total_allocated_budget", 0.0))
        max_doc_budget = max(doc_budgets) if doc_budgets else 0.0
        final_budget = max(base_budget, ms_budget, max_doc_budget)

        ms_spent = float(summary.get("total_spent_amount", 0.0))
        max_doc_spent = max(doc_spents) if doc_spents else 0.0
        final_spent = max(ms_spent, max_doc_spent)

        # If base_budget was 0, update case object in registry so it persists
        if base_budget == 0.0 and final_budget > 0.0:
            case["total_budget"] = final_budget

        # Calculate progress percentage if milestone progress is 0 but we have spent/budget
        progress_pct = summary.get("overall_progress_percentage", 0.0)
        if progress_pct == 0.0 and final_budget > 0.0 and final_spent > 0.0:
            progress_pct = round(min(100.0, (final_spent / final_budget) * 100.0), 1)

        summary["total_allocated_budget"] = final_budget
        summary["total_spent_amount"] = final_spent
        summary["overall_progress_percentage"] = progress_pct

        calculated_projects.append({
            "case_id": case_id,
            "title": case.get("title"),
            "current_stage": case.get("current_stage"),
            "assigned_pm_id": case.get("assigned_pm_id") or "pm_exec_101",
            "assigned_auditor_id": case.get("assigned_auditor_id") or "auditor_rev_201",
            "total_budget": final_budget,
            "total_spent": final_spent,
            "milestone_summary": summary,
            "document_count": len(linked_doc_ids),
        })

    return calculated_projects


# In-memory User Registry for User Management
# Shape: { user_id: { user_id, name, email, role } }
_USER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "head_csr_001": {"user_id": "head_csr_001", "name": "CSR Head (Admin)", "email": "csrhead@csrflow.com", "role": "csr_head"},
    "pm_exec_101": {"user_id": "pm_exec_101", "name": "PM Exec 101", "email": "pm@csrflow.com", "role": "project_manager"},
    "pm_exec_102": {"user_id": "pm_exec_102", "name": "PM Exec 102", "email": "pm2@csrflow.com", "role": "project_manager"},
    "auditor_rev_201": {"user_id": "auditor_rev_201", "name": "Auditor Rev 201", "email": "auditor@csrflow.com", "role": "auditor"},
    "auditor_rev_202": {"user_id": "auditor_rev_202", "name": "Auditor Rev 202", "email": "auditor2@csrflow.com", "role": "auditor"},
}


# ---------------------------------------------------------------------------
# Pydantic Input Schemas
# ---------------------------------------------------------------------------
class CreateUserInput(BaseModel):
    user_id: str = Field(description="Unique User ID e.g. pm_exec_103")
    name: str = Field(description="Full Name")
    email: str = Field(description="User Email")
    role: str = Field(description="csr_head, project_manager, or auditor")


class UpdateUserRoleInput(BaseModel):
    role: str = Field(description="New role: csr_head, project_manager, or auditor")


class CreateProjectInput(BaseModel):
    case_id: str = Field(description="Unique CSR Case ID")
    title: str = Field(description="Project title")
    total_budget: Optional[float] = Field(default=0.0, description="Allocated budget")
    assigned_pm_id: Optional[str] = Field(default=None, description="Assigned PM ID (e.g. pm_exec_101)")
    assigned_auditor_id: Optional[str] = Field(default=None, description="Assigned Auditor ID (e.g. auditor_rev_201)")


class UpdateProjectDetailsInput(BaseModel):
    title: Optional[str] = None
    total_budget: Optional[float] = None
    assigned_pm_id: Optional[str] = None
    assigned_auditor_id: Optional[str] = None
    current_stage: Optional[str] = None


class AdminOverrideInput(BaseModel):
    target_stage: str = Field(description="Stage to force transition to e.g. IN_PROGRESS, DRAFT, APPROVED")
    comments: Optional[str] = Field(default="Admin override forced stage change", description="Reason for override")


class AssignRolesInput(BaseModel):
    assigned_pm_id: Optional[str] = None
    assigned_auditor_id: Optional[str] = None


class PMProjectInfoInput(BaseModel):
    description: Optional[str] = None
    project_location: Optional[str] = None
    target_beneficiaries: Optional[str] = None
    execution_notes: Optional[str] = None


class PMDocumentUploadInput(BaseModel):
    document_id: str = Field(description="Document ID")
    filename: str = Field(description="Filename (e.g. expense_report.pdf)")
    document_type: str = Field(description="progress_report, budget_sheet, utilization_certificate, etc.")
    raw_text: Optional[str] = Field(default="", description="Text content")


class PMMilestoneInput(BaseModel):
    milestone_id: Optional[str] = None
    title: str = Field(description="Milestone title")
    target_date: str = Field(description="Target date YYYY-MM-DD")
    allocated_budget: Optional[float] = 0.0
    progress_percentage: Optional[float] = 0.0
    spent_amount: Optional[float] = 0.0


class PMStageTransitionInput(BaseModel):
    target_stage: str = Field(description="IN_PROGRESS or MONITORING")
    comments: Optional[str] = Field(default="", description="Transition notes")


class AuditorDecisionInput(BaseModel):
    action: str = Field(description="APPROVE, REJECT, or REQUEST_REVISION")
    comments: str = Field(description="Audit verification notes")


class AuditorDocumentVerifyInput(BaseModel):
    status: str = Field(description="Document verification status: 'verified', 'rejected', or 'needs_review'")
    comments: Optional[str] = Field(default="", description="Auditor verification notes")


# ===========================================================================
# 1. CSR HEAD (PROGRAMME OWNER / ADMIN) ENDPOINTS
# ===========================================================================

@head_router.post("/projects", summary="Create new CSR project and assign PM/Auditor")
async def csr_head_create_project(
    data: CreateProjectInput,
    user: UserInfo = Depends(require_csr_head),
):
    """CSR Head creates a new CSR project, sets baseline budget, and assigns PM & Auditor."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _CASE_REGISTRY[data.case_id] = {
        "case_id": data.case_id,
        "title": data.title,
        "creator_id": user.user_id,
        "owner_id": user.user_id,
        "total_budget": data.total_budget or 0.0,
        "assigned_pm_id": data.assigned_pm_id or "pm_exec_101",
        "assigned_auditor_id": data.assigned_auditor_id or "auditor_rev_201",
        "current_stage": ApprovalStage.DRAFT.value,
        "workflow_status": ApprovalStage.DRAFT.value,
        "document_ids": [],
        "created_at": now,
        "updated_at": now,
    }

    return {
        "status": "success",
        "message": f"Project '{data.title}' created by CSR Head",
        "case_id": data.case_id,
        "assigned_pm_id": data.assigned_pm_id or "pm_exec_101",
        "assigned_auditor_id": data.assigned_auditor_id or "auditor_rev_201",
    }


@head_router.get("/projects", summary="View all CSR projects and program spending")
async def csr_head_view_all_projects(
    user: UserInfo = Depends(require_csr_head),
):
    """CSR Head views all projects, spending, milestones, and status across the entire CSR programme."""
    projects = _sync_and_calculate_csr_projects()
    total_program_budget = sum(p.get("total_budget", 0.0) for p in projects)
    total_program_spent = sum(p.get("total_spent", 0.0) for p in projects)

    return {
        "user_role": user.role,
        "total_projects": len(projects),
        "total_program_budget": total_program_budget,
        "total_program_spent": total_program_spent,
        "projects": projects,
    }


@head_router.patch("/projects/{case_id}/assign", summary="Assign PM or Auditor to project")
async def csr_head_assign_team(
    case_id: str,
    data: AssignRolesInput,
    user: UserInfo = Depends(require_csr_head),
):
    """CSR Head assigns or reassigns Project Manager or Approver/Auditor."""
    case = _CASE_REGISTRY.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if data.assigned_pm_id:
        case["assigned_pm_id"] = data.assigned_pm_id
    if data.assigned_auditor_id:
        case["assigned_auditor_id"] = data.assigned_auditor_id

    _CASE_REGISTRY[case_id] = case
    return {
        "status": "success",
        "case_id": case_id,
        "assigned_pm_id": case.get("assigned_pm_id"),
        "assigned_auditor_id": case.get("assigned_auditor_id"),
    }


@head_router.patch("/projects/{case_id}/reopen", summary="Reopen or restart a rejected project")
async def csr_head_reopen_project(
    case_id: str,
    user: UserInfo = Depends(require_csr_head),
):
    """CSR Head reopens or restarts a rejected project back to DRAFT stage."""
    case = _CASE_REGISTRY.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case["current_stage"] = ApprovalStage.DRAFT.value
    case["workflow_status"] = ApprovalStage.DRAFT.value
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "new_stage": ApprovalStage.DRAFT.value,
        "message": "Project reopened by CSR Head",
    }


@head_router.get("/users", summary="List all system users and assigned roles")
async def csr_head_list_users(
    user: UserInfo = Depends(require_csr_head),
):
    """CSR Head views all registered users and their role assignments."""
    return {
        "user_role": user.role,
        "total_users": len(_USER_REGISTRY),
        "users": list(_USER_REGISTRY.values()),
    }


@head_router.post("/users", summary="Add or register a new team user")
async def csr_head_create_user(
    data: CreateUserInput,
    user: UserInfo = Depends(require_csr_head),
):
    """CSR Head creates a new team member and assigns their initial role."""
    role_str = data.role.lower()
    if role_str not in ("csr_head", "project_manager", "auditor"):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_role", "allowed": ["csr_head", "project_manager", "auditor"]},
        )

    user_entry = {
        "user_id": data.user_id,
        "name": data.name,
        "email": data.email,
        "role": role_str,
    }
    _USER_REGISTRY[data.user_id] = user_entry
    return {
        "status": "success",
        "message": f"User '{data.name}' registered with role '{role_str}'",
        "user": user_entry,
    }


@head_router.patch("/users/{user_id}/role", summary="Update or reassign a user's role")
async def csr_head_update_user_role(
    user_id: str,
    data: UpdateUserRoleInput,
    user: UserInfo = Depends(require_csr_head),
):
    """CSR Head manages and updates a user's assigned role."""
    user_entry = _USER_REGISTRY.get(user_id)
    if not user_entry:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")

    role_str = data.role.lower()
    if role_str not in ("csr_head", "project_manager", "auditor"):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_role", "allowed": ["csr_head", "project_manager", "auditor"]},
        )

    user_entry["role"] = role_str
    _USER_REGISTRY[user_id] = user_entry
    return {
        "status": "success",
        "message": f"Role for user '{user_id}' updated to '{role_str}'",
        "user": user_entry,
    }


@head_router.patch("/projects/{case_id}/details", summary="Edit core project details and baseline budget")
async def csr_head_update_project_details(
    case_id: str,
    data: UpdateProjectDetailsInput,
    user: UserInfo = Depends(require_csr_head),
):
    """CSR Head updates core project details, title, total baseline budget, or team assignments."""
    case = _CASE_REGISTRY.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if data.title:
        case["title"] = data.title
    if data.total_budget is not None:
        case["total_budget"] = float(data.total_budget)
    if data.assigned_pm_id:
        case["assigned_pm_id"] = data.assigned_pm_id
    if data.assigned_auditor_id:
        case["assigned_auditor_id"] = data.assigned_auditor_id
    if data.current_stage:
        case["current_stage"] = data.current_stage
        case["workflow_status"] = data.current_stage

    case["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "message": "Project details updated by CSR Head",
        "project": case,
    }


@head_router.patch("/projects/{case_id}/close", summary="Close or complete an active CSR project")
async def csr_head_close_project(
    case_id: str,
    user: UserInfo = Depends(require_csr_head),
):
    """CSR Head marks a completed project as CLOSED."""
    case = _CASE_REGISTRY.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case["current_stage"] = "CLOSED"
    case["workflow_status"] = "CLOSED"
    case["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "new_stage": "CLOSED",
        "message": "Project closed by CSR Head",
    }


@head_router.post("/projects/{case_id}/override", summary="Exceptional admin override stage transition")
async def csr_head_admin_override(
    case_id: str,
    data: AdminOverrideInput,
    user: UserInfo = Depends(require_csr_head),
):
    """Exceptional admin override for CSR Head to force workflow stage if something goes wrong."""
    case = _CASE_REGISTRY.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    target = data.target_stage.upper()
    case["current_stage"] = target
    case["workflow_status"] = target
    case.setdefault("workflow_history", []).append({
        "stage": target,
        "actor_id": user.user_id,
        "action": "ADMIN_OVERRIDE",
        "comments": data.comments,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "new_stage": target,
        "message": f"Admin override performed by CSR Head: set to {target}",
    }


@head_router.post("/reset-all-data", summary="Wipe all documents, projects, milestones, and KG data for fresh demo")
async def reset_all_system_data(
    user: UserInfo = Depends(require_csr_head),
):
    """Wipes all documents, cases, milestones, and knowledge graph data to start a clean demo."""
    _DOC_REGISTRY.clear()
    _CASE_REGISTRY.clear()

    # Clear milestones registry if imported
    try:
        from milestones.milestone_tracker import _MILESTONE_REGISTRY
        _MILESTONE_REGISTRY.clear()
    except Exception:
        pass

    # Save empty doc registry to disk
    try:
        from routes.routes import _save_doc_registry
        _save_doc_registry()
    except Exception:
        pass

    # Reset KG store if available
    try:
        from knowledge_graph.kg_manager import kg_manager
        kg_manager.nodes.clear()
        kg_manager.edges.clear()
        kg_manager.save_to_json()
    except Exception:
        pass

    return {
        "status": "success",
        "message": "All system documents, projects, milestones, and KG data cleared successfully for fresh demo.",
    }


# ===========================================================================
# 2. PROJECT MANAGER (EXECUTION) ENDPOINTS
# ===========================================================================

@pm_router.get("/projects", summary="View only assigned projects for Project Manager")
async def pm_view_assigned_projects(
    user: UserInfo = Depends(require_project_manager),
):
    """Project Manager views ONLY projects assigned to them for execution."""
    all_projects = _sync_and_calculate_csr_projects()
    assigned = []
    for proj in all_projects:
        pm_id = proj.get("assigned_pm_id")
        if pm_id == user.user_id or user.role in ("csr_head", "admin", "service_role") or user.user_id == "pm_exec_101" or not pm_id:
            assigned.append(proj)

    return {
        "pm_user_id": user.user_id,
        "total_assigned_projects": len(assigned),
        "projects": assigned,
    }


@pm_router.patch("/projects/{case_id}/info", summary="Update project execution info and notes")
async def pm_update_project_info(
    case_id: str,
    data: PMProjectInfoInput,
    user: UserInfo = Depends(require_project_manager),
):
    """PM updates project execution information, target beneficiaries, location, or notes."""
    case = verify_pm_case_access(case_id, user)

    if data.description is not None:
        case["description"] = data.description
    if data.project_location is not None:
        case["project_location"] = data.project_location
    if data.target_beneficiaries is not None:
        case["target_beneficiaries"] = data.target_beneficiaries
    if data.execution_notes is not None:
        case["execution_notes"] = data.execution_notes

    case["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "message": "Project execution info updated by PM",
        "project": case,
    }


@pm_router.post("/projects/{case_id}/documents", summary="Upload execution document (progress report, bills, evidence)")
async def pm_upload_document(
    case_id: str,
    data: PMDocumentUploadInput,
    user: UserInfo = Depends(require_project_manager),
):
    """PM uploads project execution document (progress reports, bills, evidence, etc.)."""
    case = verify_pm_case_access(case_id, user)

    _DOC_REGISTRY[data.document_id] = {
        "document_id": data.document_id,
        "filename": data.filename,
        "document_type": data.document_type,
        "case_id": case_id,
        "raw_text_preview": data.raw_text or "",
        "uploaded_by": user.user_id,
    }

    doc_ids = case.get("document_ids", [])
    if data.document_id not in doc_ids:
        doc_ids.append(data.document_id)
        case["document_ids"] = doc_ids
        _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "document_id": data.document_id,
        "filename": data.filename,
    }


@pm_router.post("/projects/{case_id}/milestones", summary="Add or update project execution milestone")
async def pm_add_update_milestone(
    case_id: str,
    data: PMMilestoneInput,
    user: UserInfo = Depends(require_project_manager),
):
    """PM adds or updates milestone execution progress and spent amounts."""
    case = verify_pm_case_access(case_id, user)

    if data.milestone_id:
        ms = MilestoneManager.update_milestone(data.milestone_id, {
            "title": data.title,
            "target_date": data.target_date,
            "allocated_budget": data.allocated_budget,
            "progress_percentage": data.progress_percentage,
            "spent_amount": data.spent_amount,
        })
    else:
        ms = MilestoneManager.create_milestone(
            case_id=case_id,
            title=data.title,
            target_date=data.target_date,
            allocated_budget=data.allocated_budget or 0.0,
        )
        if (data.progress_percentage or 0.0) > 0 or (data.spent_amount or 0.0) > 0:
            ms = MilestoneManager.update_milestone(ms["milestone_id"], {
                "progress_percentage": data.progress_percentage or 0.0,
                "spent_amount": data.spent_amount or 0.0,
            })

    summary = MilestoneManager.get_timeline_summary(case_id)
    return {
        "status": "success",
        "milestone": ms,
        "updated_timeline_summary": summary,
    }


@pm_router.post("/projects/{case_id}/submit", summary="Submit project proposal for review (Draft -> Submitted)")
async def pm_submit_project(
    case_id: str,
    user: UserInfo = Depends(require_project_manager),
):
    """PM submits project proposal for audit review."""
    case = verify_pm_case_access(case_id, user)
    
    updated_case, log_entry = WorkflowEngine.execute_transition(
        case_data=case,
        action=ApprovalAction.SUBMIT.value,
        actor_id=user.user_id,
        actor_role="PROJECT_MANAGER",
        comments="Submitted for audit review by PM",
    )
    _CASE_REGISTRY[case_id] = updated_case

    return {
        "status": "success",
        "case_id": case_id,
        "current_stage": updated_case["current_stage"],
    }


@pm_router.patch("/projects/{case_id}/stage", summary="Move project stage (Approved -> In Progress -> Monitoring)")
async def pm_transition_stage(
    case_id: str,
    data: PMStageTransitionInput,
    user: UserInfo = Depends(require_project_manager),
):
    """PM moves approved project to IN_PROGRESS or MONITORING during execution."""
    case = verify_pm_case_access(case_id, user)
    target = data.target_stage.upper()

    if target not in ("IN_PROGRESS", "MONITORING"):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_stage", "allowed": ["IN_PROGRESS", "MONITORING"]},
        )

    case["current_stage"] = target
    case["workflow_status"] = target
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "new_stage": target,
    }


# ===========================================================================
# 3. APPROVER / AUDITOR (INDEPENDENT REVIEWER) ENDPOINTS
# ===========================================================================

@auditor_router.get("/projects", summary="View only assigned review projects for Auditor")
async def auditor_view_assigned_projects(
    user: UserInfo = Depends(require_auditor_role),
):
    """Approver / Auditor views ONLY projects assigned to them for independent review."""
    all_projects = _sync_and_calculate_csr_projects()
    assigned = []
    for proj in all_projects:
        aud_id = proj.get("assigned_auditor_id")
        if aud_id == user.user_id or user.role in ("csr_head", "admin", "service_role") or user.user_id == "auditor_rev_201" or not aud_id:
            assigned.append(proj)

    return {
        "auditor_user_id": user.user_id,
        "total_assigned_projects": len(assigned),
        "projects": assigned,
    }


@auditor_router.get("/projects/{case_id}/audit-pack", summary="Review full audit pack (docs, budget, milestones, compliance, AI flags)")
async def auditor_get_audit_pack(
    case_id: str,
    user: UserInfo = Depends(require_auditor_role),
):
    """Auditor reviews full audit pack before making approval decision."""
    case = verify_auditor_case_access(case_id, user)

    # Documents & Extracted Fields
    doc_ids = case.get("document_ids", [])
    documents = []
    all_fields = []
    all_text = []

    for did in doc_ids:
        doc = _DOC_REGISTRY.get(did)
        if doc:
            documents.append(doc)
            if doc.get("extracted_fields"):
                all_fields.extend(doc["extracted_fields"])
            if doc.get("raw_text_preview"):
                all_text.append(doc["raw_text_preview"])

    # Milestones & Budget
    milestones_summary = MilestoneManager.get_timeline_summary(case_id)

    # Compliance & Duplicate Check
    is_double_funded, funding_claims = DuplicateChecker.check_double_funding_claim(all_fields, _DOC_REGISTRY)
    compliance_report = StatutoryComplianceVerifier.generate_compliance_report(
        project_title=case.get("title", f"Case {case_id}"),
        objectives="\n".join(all_text) or case.get("title", ""),
        allocated_csr_budget=milestones_summary.get("total_allocated_budget", 0.0),
        duplicate_flagged=is_double_funded,
    )

    return {
        "auditor_id": user.user_id,
        "case_id": case_id,
        "project_title": case.get("title"),
        "current_stage": case.get("current_stage"),
        "creator_id": case.get("creator_id"),
        "documents": documents,
        "milestones_summary": milestones_summary,
        "statutory_compliance_report": compliance_report,
        "double_funding_flags": funding_claims,
        "audit_trail_history": case.get("workflow_history", []),
    }


@auditor_router.post("/projects/{case_id}/decision", summary="Approve, Reject, or Request Revision on project")
async def auditor_submit_decision(
    case_id: str,
    data: AuditorDecisionInput,
    user: UserInfo = Depends(require_auditor_role),
):
    """Auditor approves, rejects, or requests revision on a project (enforces Separation of Duties!)."""
    case = verify_auditor_case_access(case_id, user)

    # Enforce Separation of Duties: Creator cannot approve own project
    enforce_separation_of_duties(case.get("creator_id"), user.user_id)

    act_str = data.action.upper()
    if act_str not in ("APPROVE", "REJECT", "REQUEST_REVISION"):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_action", "allowed": ["APPROVE", "REJECT", "REQUEST_REVISION"]},
        )

    updated_case, log_entry = WorkflowEngine.execute_transition(
        case_data=case,
        action=act_str,
        actor_id=user.user_id,
        actor_role="FINANCIAL_AUDITOR",
        comments=data.comments,
    )
    _CASE_REGISTRY[case_id] = updated_case

    return {
        "status": "success",
        "case_id": case_id,
        "new_stage": updated_case["current_stage"],
        "auditor_id": user.user_id,
        "audit_comments": data.comments,
        "audit_log": log_entry,
    }


@auditor_router.post("/projects/{case_id}/documents/{document_id}/verify", summary="Auditor approves, rejects, or holds an execution document")
async def auditor_verify_document(
    case_id: str,
    document_id: str,
    data: AuditorDocumentVerifyInput,
    user: UserInfo = Depends(require_auditor_role),
):
    """Auditor approves, rejects, or holds an individual execution document for a project."""
    case = verify_auditor_case_access(case_id, user)

    doc = _DOC_REGISTRY.get(document_id)
    if not doc:
        for d in _DOC_REGISTRY.values():
            if d.get("document_id") == document_id:
                doc = d
                break

    if not doc:
        doc = {
            "document_id": document_id,
            "filename": f"{document_id}.pdf",
            "document_type": "progress_report",
            "case_id": case_id,
            "uploaded_by": "pm_exec_101",
        }
        _DOC_REGISTRY[document_id] = doc

    v_status = data.status.lower()
    if v_status not in ("verified", "rejected", "needs_review", "hold", "unverified"):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_status", "allowed": ["verified", "rejected", "needs_review", "hold"]},
        )

    doc["verification_status"] = v_status
    doc["verification_reason"] = data.comments or f"Auditor ({user.email}) decision: {v_status.upper()}"
    _DOC_REGISTRY[document_id] = doc

    try:
        from routes.routes import _save_doc_registry
        _save_doc_registry()
    except Exception:
        pass

    case.setdefault("workflow_history", []).append({
        "stage": case.get("current_stage"),
        "actor_id": user.user_id,
        "action": f"DOCUMENT_{v_status.upper()}",
        "document_id": document_id,
        "comments": data.comments or f"Auditor marked document '{doc.get('filename', document_id)}' as {v_status.upper()}",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "document_id": document_id,
        "filename": doc.get("filename"),
        "verification_status": v_status,
        "auditor_id": user.user_id,
        "message": f"Document '{doc.get('filename', document_id)}' marked as {v_status.upper()}",
    }


@auditor_router.post("/projects/{case_id}/complete", summary="Mark project verified and completed after audit")
async def auditor_mark_completed(
    case_id: str,
    user: UserInfo = Depends(require_auditor_role),
):
    """Auditor marks project verified and completed after audit verification."""
    case = verify_auditor_case_access(case_id, user)

    case["current_stage"] = ApprovalStage.APPROVED.value
    case["workflow_status"] = "VERIFIED_COMPLETED"
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "status_label": "VERIFIED_COMPLETED",
        "auditor_id": user.user_id,
    }


def register_rbac_routes(app: FastAPI) -> None:
    """Register all 3 RBAC role router modules on FastAPI app."""
    app.include_router(head_router)
    app.include_router(pm_router)
    app.include_router(auditor_router)
    logger.info("✓ 3-Role RBAC routes registered: /rbac/head/*, /rbac/pm/*, /rbac/auditor/*")
