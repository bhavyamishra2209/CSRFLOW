"""
CSR Approval Workflow API Routes.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth.auth import get_current_user, UserInfo
from routes.routes import _DOC_REGISTRY
from routes.case_routes import _CASE_REGISTRY, REQUIRED_CSR_DOCUMENTS
from workflow.approval_engine import (
    WorkflowEngine,
    ApprovalStage,
    ApprovalAction,
    STAGE_REQUIRED_ROLES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cases", tags=["CSR Approval Workflow"])


class WorkflowSubmitInput(BaseModel):
    comments: Optional[str] = Field(default=None, description="Optional submission note or summary")


class WorkflowActionInput(BaseModel):
    action: str = Field(description="Workflow action: APPROVE, REJECT, REQUEST_REVISION, RESUBMIT")
    comments: Optional[str] = Field(default=None, description="Reviewer feedback or approval comments")
    reviewer_role: Optional[str] = Field(default="CSR_OFFICER", description="Role of the reviewer")


@router.post("/{case_id}/workflow/submit", summary="Submit CSR case for approval review")
async def submit_case_workflow(
    case_id: str,
    data: Optional[WorkflowSubmitInput] = None,
    user: UserInfo = Depends(get_current_user),
):
    """
    Submit a CSR case from DRAFT or REVISION_REQUESTED state for governance approval.
    Automatically validates CSR document completeness.
    """
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    current_stage = case.get("current_stage", ApprovalStage.DRAFT.value)
    action = ApprovalAction.RESUBMIT.value if current_stage == ApprovalStage.REVISION_REQUESTED.value else ApprovalAction.SUBMIT.value

    if not WorkflowEngine.can_transition(current_stage, action):
        allowed = WorkflowEngine.get_allowed_actions(current_stage)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_transition",
                "message": f"Cannot submit case in '{current_stage}' stage. Allowed actions: {allowed}",
            },
        )

    # Validate document completeness
    doc_ids = case.get("document_ids", [])
    present_types = set()
    for did in doc_ids:
        doc = _DOC_REGISTRY.get(did)
        if doc and doc.get("document_type"):
            present_types.add(doc["document_type"])

    missing_required = [dt for dt in REQUIRED_CSR_DOCUMENTS if dt not in present_types]
    
    metadata = {
        "document_count": len(doc_ids),
        "present_types": list(present_types),
        "missing_required_documents": missing_required,
        "is_complete": len(missing_required) == 0,
    }

    try:
        updated_case, log_entry = WorkflowEngine.execute_transition(
            case_data=case,
            action=action,
            actor_id=user.user_id,
            actor_role=user.role,
            comments=(data.comments if data else None) or "CSR case submitted for review",
            metadata=metadata,
        )
        _CASE_REGISTRY[case_id] = updated_case
        return {
            "status": "success",
            "case_id": case_id,
            "current_stage": updated_case["current_stage"],
            "audit_log": log_entry,
            "document_validation": metadata,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "workflow_error", "message": str(e)},
        )


@router.post("/{case_id}/workflow/action", summary="Execute approval workflow action")
async def execute_workflow_action(
    case_id: str,
    data: WorkflowActionInput,
    user: UserInfo = Depends(get_current_user),
):
    """
    Execute an approval action (APPROVE, REJECT, REQUEST_REVISION, RESUBMIT) on a case.
    Requires appropriate stage authority.
    """
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    current_stage = case.get("current_stage", ApprovalStage.DRAFT.value)
    
    if not WorkflowEngine.can_transition(current_stage, data.action):
        allowed = WorkflowEngine.get_allowed_actions(current_stage)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_action",
                "message": f"Action '{data.action}' is not allowed for stage '{current_stage}'. Allowed: {allowed}",
            },
        )

    try:
        updated_case, log_entry = WorkflowEngine.execute_transition(
            case_data=case,
            action=data.action,
            actor_id=user.user_id,
            actor_role=data.reviewer_role or user.role,
            comments=data.comments,
        )
        _CASE_REGISTRY[case_id] = updated_case
        return {
            "status": "success",
            "case_id": case_id,
            "previous_stage": log_entry["previous_stage"],
            "current_stage": updated_case["current_stage"],
            "action_taken": data.action,
            "audit_log": log_entry,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "workflow_error", "message": str(e)},
        )


@router.get("/{case_id}/workflow", summary="Get case workflow state & allowed actions")
async def get_case_workflow_state(
    case_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Get current workflow stage, status, allowed next actions, and required roles for a case."""
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    current_stage = case.get("current_stage", ApprovalStage.DRAFT.value)
    allowed_actions = WorkflowEngine.get_allowed_actions(current_stage)
    
    try:
        stg_enum = ApprovalStage(current_stage)
        required_roles = STAGE_REQUIRED_ROLES.get(stg_enum, [])
    except ValueError:
        required_roles = []

    history = case.get("workflow_history", [])

    return {
        "case_id": case_id,
        "title": case.get("title"),
        "current_stage": current_stage,
        "workflow_status": case.get("workflow_status", current_stage),
        "allowed_actions": allowed_actions,
        "stage_required_roles": required_roles,
        "total_audit_records": len(history),
        "last_updated": case.get("updated_at"),
    }


@router.get("/{case_id}/workflow/history", summary="Get case workflow audit trail history")
async def get_case_workflow_history(
    case_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Get complete step-by-step immutable audit log trail for a case."""
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    history = case.get("workflow_history", [])
    return {
        "case_id": case_id,
        "current_stage": case.get("current_stage", ApprovalStage.DRAFT.value),
        "total_steps": len(history),
        "history": history,
    }


# Standalone router for pending workflows endpoint under /workflows
workflow_pending_router = APIRouter(prefix="/workflows", tags=["CSR Approval Workflow"])


@workflow_pending_router.get("/pending", summary="List cases pending review at a specific stage")
async def list_pending_workflows(
    stage: Optional[str] = Query(default=None, description="Filter by ApprovalStage (e.g. CSR_COMMITTEE_REVIEW)"),
    user: UserInfo = Depends(get_current_user),
):
    """List all CSR project cases currently pending approval review."""
    pending_cases = []
    
    for case_id, case in _CASE_REGISTRY.items():
        stg = case.get("current_stage", ApprovalStage.DRAFT.value)
        # Exclude terminal states by default unless requested
        if stage:
            if stg.upper() == stage.upper():
                pending_cases.append({
                    "case_id": case_id,
                    "title": case.get("title"),
                    "current_stage": stg,
                    "document_count": len(case.get("document_ids", [])),
                    "allowed_actions": WorkflowEngine.get_allowed_actions(stg),
                })
        else:
            if stg not in (ApprovalStage.APPROVED.value, ApprovalStage.REJECTED.value):
                pending_cases.append({
                    "case_id": case_id,
                    "title": case.get("title"),
                    "current_stage": stg,
                    "document_count": len(case.get("document_ids", [])),
                    "allowed_actions": WorkflowEngine.get_allowed_actions(stg),
                })

    return {
        "total_pending": len(pending_cases),
        "filter_stage": stage,
        "cases": pending_cases,
    }


def register_workflow_routes(app: FastAPI) -> None:
    """Register workflow routers on FastAPI app."""
    app.include_router(router)
    app.include_router(workflow_pending_router)
    logger.info("✓ CSR Approval Workflow routes registered: /cases/{id}/workflow/* and /workflows/pending")
