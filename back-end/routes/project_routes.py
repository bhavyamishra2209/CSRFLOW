"""
CSR Project Lifecycle Management - API Routes
Feature #1: CSR Project Lifecycle Management

Endpoints for CSR Project creation, listing, details, updating,
lifecycle stage transitions, document linking, and audit trail inspection.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth.auth import UserInfo, get_current_user, _admin_ids
from project.models import (
    CSRProject,
    LinkDocumentRequest,
    ProjectAuditEntry,
    ProjectCreateRequest,
    ProjectStage,
    ProjectUpdateRequest,
    StageTransitionRequest,
)
from project.service import project_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["CSR Projects"])


def _check_is_admin(user: UserInfo) -> bool:
    return user.role == "service_role" or user.user_id in _admin_ids()


@router.post(
    "",
    response_model=CSRProject,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new CSR project in DRAFT stage",
)
async def create_project(
    req: ProjectCreateRequest,
    user: UserInfo = Depends(get_current_user),
):
    """
    Create a new CSR project.
    - Initial stage is always `DRAFT`.
    - Generates human-readable `project_code` (CSR-YYYY-XXXXX) and UUID `project_id`.
    - Sets `owner_id` to the authenticated user.
    - Appends initial stage history and logs `PROJECT_CREATED` audit event.
    """
    try:
        project = project_service.create_project(req, user_id=user.user_id)
        logger.info(f"User {user.user_id} created CSR project {project.project_code} ({project.project_id})")
        return project
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "create_project_failed", "message": str(e)},
        )


@router.get(
    "",
    response_model=List[CSRProject],
    summary="List CSR projects",
)
async def list_projects(
    stage: Optional[ProjectStage] = Query(None, description="Filter projects by stage"),
    user: UserInfo = Depends(get_current_user),
):
    """
    List CSR projects owned by the authenticated user.
    Admins can view projects across all users.
    Supports filtering by stage.
    """
    is_admin = _check_is_admin(user)
    return project_service.list_projects(user_id=user.user_id, stage=stage, is_admin=is_admin)


@router.get(
    "/{project_id}",
    response_model=CSRProject,
    summary="Get details of a CSR project",
)
async def get_project(
    project_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """
    Retrieve full details of a CSR project including current stage and stage history.
    """
    is_admin = _check_is_admin(user)
    return project_service.get_project(project_id, user_id=user.user_id, is_admin=is_admin)


@router.put(
    "/{project_id}",
    response_model=CSRProject,
    summary="Update project metadata",
)
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    user: UserInfo = Depends(get_current_user),
):
    """
    Update project metadata.
    Enforces stage-based editability restrictions:
    - `DRAFT`: Fully editable.
    - `SUBMITTED`, `UNDER_EVALUATION`: Locked for review/evaluation.
    - `APPROVED`, `FUNDED`, `IN_PROGRESS`, `UNDER_REVIEW`: Restricted updates (description, location only).
    - `COMPLETED`, `CLOSED`: Read-only.
    """
    is_admin = _check_is_admin(user)
    return project_service.update_project(project_id, req, user_id=user.user_id, is_admin=is_admin)


@router.post(
    "/{project_id}/stage",
    response_model=CSRProject,
    summary="Transition project to a new lifecycle stage",
)
async def transition_stage(
    project_id: str,
    req: StageTransitionRequest,
    user: UserInfo = Depends(get_current_user),
):
    """
    Transition project to a new lifecycle stage.
    Validates against the approved 9-stage state machine matrix.
    Appends to stage history and writes to audit log.
    """
    is_admin = _check_is_admin(user)
    return project_service.transition_stage(
        project_id,
        target_stage=req.target_stage,
        comments=req.comments,
        user_id=user.user_id,
        is_admin=is_admin,
    )


@router.get(
    "/{project_id}/stages/allowed",
    response_model=List[ProjectStage],
    summary="Get allowed next stages for project",
)
async def get_allowed_stages(
    project_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """
    Returns legal next stages that can follow the project's current stage.
    Returns an empty list for `CLOSED` terminal state.
    """
    is_admin = _check_is_admin(user)
    return project_service.get_allowed_stages(project_id, user_id=user.user_id, is_admin=is_admin)


@router.post(
    "/{project_id}/documents",
    response_model=CSRProject,
    summary="Link an existing document to the project",
)
async def link_document(
    project_id: str,
    req: LinkDocumentRequest,
    user: UserInfo = Depends(get_current_user),
):
    """
    Link an existing document ID to this CSR project.
    Validates document existence in the system and user ownership.
    """
    is_admin = _check_is_admin(user)
    return project_service.link_document(
        project_id,
        document_id=req.document_id,
        user_id=user.user_id,
        is_admin=is_admin,
    )


@router.delete(
    "/{project_id}/documents/{doc_id}",
    response_model=CSRProject,
    summary="Unlink a document from the project",
)
async def unlink_document(
    project_id: str,
    doc_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """
    Unlink a document from this CSR project.
    """
    is_admin = _check_is_admin(user)
    return project_service.unlink_document(
        project_id,
        document_id=doc_id,
        user_id=user.user_id,
        is_admin=is_admin,
    )


@router.get(
    "/{project_id}/documents",
    response_model=List[Dict[str, Any]],
    summary="List all documents linked to the project",
)
async def get_project_documents(
    project_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """
    List metadata for all documents linked to this project.
    """
    is_admin = _check_is_admin(user)
    return project_service.get_linked_documents(project_id, user_id=user.user_id, is_admin=is_admin)


@router.get(
    "/{project_id}/audit",
    response_model=List[ProjectAuditEntry],
    summary="Get project audit trail",
)
async def get_project_audit(
    project_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """
    Get full audit trail of lifecycle actions performed on this project.
    """
    is_admin = _check_is_admin(user)
    return project_service.get_audit_trail(project_id, user_id=user.user_id, is_admin=is_admin)


def register_project_routes(app) -> None:
    """Register CSR project routes on the FastAPI app. Called from main.py."""
    app.include_router(router)
    logger.info("✓ CSR Project routes registered: /projects")
