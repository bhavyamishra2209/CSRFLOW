"""
Independent Auditor & Approver Role-Based Access Control API Routes.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.auth import get_current_user, require_auditor, UserInfo
from routes.case_routes import _CASE_REGISTRY
from routes.routes import _DOC_REGISTRY
from workflow.approval_engine import WorkflowEngine, ApprovalStage, ApprovalAction
from milestones.milestone_tracker import MilestoneManager
from compliance.compliance_verifier import StatutoryComplianceVerifier
from compliance.duplicate_checker import DuplicateChecker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auditor", tags=["Auditor / Approver Role-Based Control"])
case_auditor_router = APIRouter(prefix="/cases", tags=["Auditor / Approver Role-Based Control"])


class AuditorDecisionInput(BaseModel):
    action: str = Field(description="APPROVE, REJECT, or REQUEST_REVISION")
    comments: str = Field(description="Auditor verification notes and audit rationale")


class AssignAuditorInput(BaseModel):
    auditor_id: str = Field(description="Auditor user ID (e.g. auditor_user_456)")


class AssignPMInput(BaseModel):
    pm_id: str = Field(description="Project Manager user ID")


@router.get("/cases", summary="List project cases assigned to the Auditor")
async def list_assigned_auditor_cases(
    user: UserInfo = Depends(require_auditor),
):
    """List all CSR project cases assigned to the logged-in Auditor for independent review."""
    assigned_cases = []
    for case_id, case in _CASE_REGISTRY.items():
        assigned_id = case.get("assigned_auditor_id")
        # Include if assigned to this auditor, or if user is dev auditor / service_role / admin
        if assigned_id == user.user_id or user.role in ("service_role", "admin") or user.user_id == "auditor_user_456" or not assigned_id:
            assigned_cases.append({
                "case_id": case_id,
                "title": case.get("title"),
                "current_stage": case.get("current_stage", ApprovalStage.DRAFT.value),
                "workflow_status": case.get("workflow_status", ApprovalStage.DRAFT.value),
                "assigned_auditor_id": assigned_id or "auditor_user_456",
                "document_count": len(case.get("document_ids", [])),
                "updated_at": case.get("updated_at"),
            })

    return {
        "auditor_user_id": user.user_id,
        "auditor_role": user.role,
        "total_assigned_cases": len(assigned_cases),
        "cases": assigned_cases,
    }


@router.get("/cases/{case_id}/review-dashboard", summary="Comprehensive Auditor Review Control Center")
async def get_auditor_review_dashboard(
    case_id: str,
    user: UserInfo = Depends(require_auditor),
):
    """
    Independent Auditor Dashboard aggregating:
    - Core project metadata & workflow state
    - Uploaded documents, OCR text previews, and extracted fields
    - Milestone progress & financial budget utilization
    - Statutory compliance scores & AI duplicate flags
    - Allowed review decision actions
    - Complete workflow audit history log
    """
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    # 1. Associated Documents & Fields
    doc_ids = case.get("document_ids", [])
    documents = []
    all_fields = []
    all_text = []

    for did in doc_ids:
        doc = _DOC_REGISTRY.get(did)
        if doc:
            documents.append({
                "document_id": did,
                "filename": doc.get("filename"),
                "document_type": doc.get("document_type"),
                "is_verified": doc.get("is_verified", False),
                "verification_score": doc.get("verification_score", 0.0),
                "field_count": len(doc.get("extracted_fields", [])),
            })
            if doc.get("extracted_fields"):
                all_fields.extend(doc["extracted_fields"])
            if doc.get("raw_text_preview"):
                all_text.append(doc["raw_text_preview"])

    # 2. Milestone & Financial Progress
    milestone_summary = MilestoneManager.get_timeline_summary(case_id)

    # 3. Compliance & Duplicate Flags
    is_double_funded, funding_claims = DuplicateChecker.check_double_funding_claim(all_fields, _DOC_REGISTRY)
    compliance_report = case.get("compliance_report")
    if not compliance_report:
        compliance_report = StatutoryComplianceVerifier.generate_compliance_report(
            project_title=case.get("title", f"Case {case_id}"),
            objectives="\n".join(all_text) or case.get("title", ""),
            allocated_csr_budget=milestone_summary.get("total_allocated_budget", 0.0),
            duplicate_flagged=is_double_funded,
        )

    # 4. Workflow State & Allowed Auditor Actions
    curr_stage = case.get("current_stage", ApprovalStage.DRAFT.value)
    history = case.get("workflow_history", [])

    allowed_actions = []
    if curr_stage in (
        ApprovalStage.SUBMITTED.value,
        ApprovalStage.DOCUMENT_VERIFICATION.value,
        ApprovalStage.CSR_COMMITTEE_REVIEW.value,
        ApprovalStage.FINANCIAL_AUDIT.value,
    ):
        allowed_actions = ["APPROVE", "REJECT", "REQUEST_REVISION"]

    return {
        "auditor_id": user.user_id,
        "case_id": case_id,
        "project_title": case.get("title"),
        "current_stage": curr_stage,
        "assigned_auditor_id": case.get("assigned_auditor_id", "auditor_user_456"),
        "documents": documents,
        "milestone_summary": milestone_summary,
        "compliance_and_risk": compliance_report,
        "double_funding_flags": funding_claims,
        "allowed_auditor_actions": allowed_actions,
        "audit_trail_history": history,
    }


@router.post("/cases/{case_id}/decision", summary="Submit formal Auditor review decision")
async def submit_auditor_decision(
    case_id: str,
    data: AuditorDecisionInput,
    user: UserInfo = Depends(require_auditor),
):
    """Submit formal Auditor decision (APPROVE, REJECT, REQUEST_REVISION) with audit comments."""
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    action_str = data.action.upper()
    if action_str not in ("APPROVE", "REJECT", "REQUEST_REVISION"):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_action", "allowed": ["APPROVE", "REJECT", "REQUEST_REVISION"]},
        )

    try:
        updated_case, log_entry = WorkflowEngine.execute_transition(
            case_data=case,
            action=action_str,
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
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "workflow_transition_error", "message": str(e)},
        )


@case_auditor_router.post("/{case_id}/assign-auditor", summary="Assign Auditor to a CSR project case")
async def assign_auditor_to_case(
    case_id: str,
    data: AssignAuditorInput,
    user: UserInfo = Depends(get_current_user),
):
    """Assign an Auditor to a CSR project case for independent verification (Admin/CSR Head action)."""
    if user.role == "auditor":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "message": "Auditors cannot self-assign or reassign cases. Only CSR Head or Admin can assign Auditors.",
            },
        )

    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    case["assigned_auditor_id"] = data.auditor_id
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "assigned_auditor_id": data.auditor_id,
    }


@case_auditor_router.patch("/{case_id}/assign-pm", summary="Assign Project Manager (Restricted for Auditor)")
async def assign_pm_to_case(
    case_id: str,
    data: AssignPMInput,
    user: UserInfo = Depends(get_current_user),
):
    """Assign Project Manager to a case (Restricted for Auditor role)."""
    if user.role == "auditor":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "message": "Auditor role cannot assign Project Managers or team members. Only CSR Head can assign PMs.",
            },
        )

    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    case["assigned_pm_id"] = data.pm_id
    _CASE_REGISTRY[case_id] = case

    return {
        "status": "success",
        "case_id": case_id,
        "assigned_pm_id": data.pm_id,
    }


def register_auditor_routes(app: FastAPI) -> None:
    """Register Auditor RBAC routes on FastAPI app."""
    app.include_router(router)
    app.include_router(case_auditor_router)
    logger.info("✓ Auditor RBAC routes registered: /auditor/* and /cases/{id}/assign-auditor")
