"""
CSR Project routes — CSRFlow

POST   /projects                          csr_head — create project
GET    /projects                          all roles — list (scoped by role)
GET    /projects/{id}                     all roles — get single project
PUT    /projects/{id}                     csr_head / pm — update fields
PUT    /projects/{id}/assign              csr_head — assign pm + approver
POST   /projects/{id}/stage              role-gated — transition stage
POST   /projects/{id}/milestones          csr_head / pm — add milestone
PUT    /projects/{id}/milestones/{mid}    csr_head / pm — update milestone
GET    /projects/{id}/history             csr_head / approver — stage history
GET    /projects/stats/summary            csr_head — aggregate stats
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from auth.auth import UserInfo, get_current_user_with_role, require_role, require_admin
from csr.project_lifecycle import (
    ProjectCreate, ProjectUpdate, AssignMembers,
    StageTransition, ProjectResponse, MilestoneCreate, MilestoneUpdate,
    ProjectStage, validate_stage_transition,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["CSR Projects"])


# ---------------------------------------------------------------------------
# Supabase REST helpers
# ---------------------------------------------------------------------------

def _sb_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip().rstrip("/")

def _sb_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

def _hdrs(prefer: str = "return=representation") -> Dict[str, str]:
    key = _sb_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": prefer,
    }


async def _fetch_project(project_id: str) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(
            f"{_sb_url()}/rest/v1/csr_projects",
            params={"project_id": f"eq.{project_id}", "select": "*"},
            headers=_hdrs(),
        )
    if resp.status_code == 200:
        data = resp.json()
        return data[0] if data else None
    return None


def _enrich(p: Dict[str, Any]) -> Dict[str, Any]:
    """Add stage_label and normalise list fields."""
    p["stage_label"] = ProjectStage.LABELS.get(p.get("stage", ""), "")
    p.setdefault("milestones", [])
    p.setdefault("documents", [])
    p.setdefault("impact_data", {})
    return p


def _check_project_access(project: Dict[str, Any], user: UserInfo) -> None:
    """Raise 404 if the user has no business seeing this project."""
    if user.csr_role == "csr_head":
        return
    uid = user.user_id
    if uid in (project.get("assigned_pm"), project.get("assigned_approver")):
        return
    raise HTTPException(status_code=404, detail="Project not found.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=201, summary="Create a project (CSR Head only)")
async def create_project(
    body: ProjectCreate,
    user: UserInfo = Depends(require_role("csr_head")),
):
    payload = {
        "project_id":        str(uuid.uuid4()),
        "title":             body.title,
        "domain":            body.domain,
        "description":       body.description,
        "budget":            body.budget,
        "stage":             ProjectStage.DRAFT,
        "created_by":        user.user_id,
        "milestones": [
            {
                "milestone_id":     str(uuid.uuid4()),
                "title":            m.title,
                "description":      m.description,
                "target_date":      m.target_date,
                "budget_allocated": m.budget_allocated,
                "deliverables":     m.deliverables,
                "status":           "pending",
                "budget_used":      0.0,
                "completion_date":  None,
            }
            for m in body.milestones
        ],
        "documents":   [],
        "impact_data": {},
        "stage_history": [
            {
                "from_stage": None,
                "to_stage":   ProjectStage.DRAFT,
                "actor_id":   user.user_id,
                "actor_role": user.csr_role,
                "comment":    "Project created.",
                "at":         datetime.now(timezone.utc).isoformat(),
            }
        ],
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{_sb_url()}/rest/v1/csr_projects",
            json=payload,
            headers=_hdrs(),
        )

    if resp.status_code not in (200, 201):
        logger.error(f"Create project failed {resp.status_code}: {resp.text}")
        raise HTTPException(status_code=500, detail="Failed to create project.")

    data = resp.json()
    project = data[0] if isinstance(data, list) else data
    return _enrich(project)


@router.get("", summary="List projects (scoped by role)")
async def list_projects(user: UserInfo = Depends(get_current_user_with_role)):
    async with httpx.AsyncClient(timeout=10.0) as client:
        if user.csr_role == "csr_head":
            params = {"select": "*", "order": "created_at.desc"}
        elif user.csr_role == "project_manager":
            params = {
                "select": "*",
                "assigned_pm": f"eq.{user.user_id}",
                "order": "created_at.desc",
            }
        elif user.csr_role == "approver":
            params = {
                "select": "*",
                "assigned_approver": f"eq.{user.user_id}",
                "order": "created_at.desc",
            }
        else:
            return []

        resp = await client.get(
            f"{_sb_url()}/rest/v1/csr_projects",
            params=params,
            headers=_hdrs(""),
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch projects.")

    return [_enrich(p) for p in resp.json()]


@router.get("/stats/summary", summary="Aggregate stats (CSR Head only)")
async def project_stats(_admin: UserInfo = Depends(require_role("csr_head"))):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{_sb_url()}/rest/v1/csr_projects",
            params={"select": "stage,budget"},
            headers=_hdrs(""),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch stats.")

    projects = resp.json()
    total = len(projects)
    by_stage: Dict[str, int] = {}
    total_budget = 0.0
    for p in projects:
        s = p.get("stage", "unknown")
        by_stage[s] = by_stage.get(s, 0) + 1
        total_budget += float(p.get("budget") or 0)

    return {
        "total_projects":  total,
        "by_stage":        by_stage,
        "total_budget":    total_budget,
        "active_projects": by_stage.get("in_progress", 0) + by_stage.get("monitoring", 0),
    }


@router.get("/{project_id}", summary="Get a single project")
async def get_project(
    project_id: str,
    user: UserInfo = Depends(get_current_user_with_role),
):
    project = await _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _check_project_access(project, user)
    return _enrich(project)


@router.put("/{project_id}", summary="Update project fields (CSR Head or PM)")
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: UserInfo = Depends(require_role("csr_head", "project_manager")),
):
    project = await _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _check_project_access(project, user)

    patch: Dict[str, Any] = {k: v for k, v in body.dict().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="Nothing to update.")

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.patch(
            f"{_sb_url()}/rest/v1/csr_projects",
            params={"project_id": f"eq.{project_id}"},
            json=patch,
            headers=_hdrs(),
        )

    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail="Failed to update project.")

    updated = await _fetch_project(project_id)
    return _enrich(updated)


@router.put("/{project_id}/assign", summary="Assign PM + Approver (CSR Head only)")
async def assign_members(
    project_id: str,
    body: AssignMembers,
    user: UserInfo = Depends(require_role("csr_head")),
):
    project = await _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    patch: Dict[str, Any] = {}
    if body.assigned_pm is not None:
        patch["assigned_pm"] = body.assigned_pm
    if body.assigned_approver is not None:
        patch["assigned_approver"] = body.assigned_approver

    if not patch:
        raise HTTPException(status_code=400, detail="Provide at least one assignment.")

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.patch(
            f"{_sb_url()}/rest/v1/csr_projects",
            params={"project_id": f"eq.{project_id}"},
            json=patch,
            headers=_hdrs(),
        )

    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail="Failed to assign members.")

    updated = await _fetch_project(project_id)
    return _enrich(updated)


@router.post("/{project_id}/stage", summary="Transition project stage")
async def transition_stage(
    project_id: str,
    body: StageTransition,
    user: UserInfo = Depends(get_current_user_with_role),
):
    project = await _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _check_project_access(project, user)

    current_stage = project.get("stage", ProjectStage.DRAFT)

    try:
        validate_stage_transition(
            current=current_stage,
            requested=body.new_stage,
            actor_role=user.csr_role,
            actor_id=user.user_id,
            project_creator_id=project.get("created_by"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Append to history
    history: List[Dict] = project.get("stage_history") or []
    history.append({
        "from_stage": current_stage,
        "to_stage":   body.new_stage,
        "actor_id":   user.user_id,
        "actor_role": user.csr_role,
        "comment":    body.comment,
        "at":         datetime.now(timezone.utc).isoformat(),
    })

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.patch(
            f"{_sb_url()}/rest/v1/csr_projects",
            params={"project_id": f"eq.{project_id}"},
            json={"stage": body.new_stage, "stage_history": history},
            headers=_hdrs(),
        )

        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=500, detail="Failed to update stage.")

        # Write to audit log
        try:
            await client.post(
                f"{_sb_url()}/rest/v1/stage_transitions",
                json={
                    "project_id": project_id,
                    "from_stage": current_stage,
                    "to_stage":   body.new_stage,
                    "actor_id":   user.user_id,
                    "actor_role": user.csr_role,
                    "comment":    body.comment,
                },
                headers=_hdrs(),
            )
        except Exception:
            pass  # audit log failure is non-fatal

    updated = await _fetch_project(project_id)
    return _enrich(updated)


@router.post(
    "/{project_id}/milestones",
    status_code=201,
    summary="Add a milestone (CSR Head or PM)",
)
async def add_milestone(
    project_id: str,
    body: MilestoneCreate,
    user: UserInfo = Depends(require_role("csr_head", "project_manager")),
):
    project = await _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _check_project_access(project, user)

    milestones: List[Dict] = project.get("milestones") or []
    new_milestone = {
        "milestone_id":     str(uuid.uuid4()),
        "title":            body.title,
        "description":      body.description,
        "target_date":      body.target_date,
        "budget_allocated": body.budget_allocated,
        "deliverables":     body.deliverables,
        "status":           "pending",
        "budget_used":      0.0,
        "completion_date":  None,
    }
    milestones.append(new_milestone)

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.patch(
            f"{_sb_url()}/rest/v1/csr_projects",
            params={"project_id": f"eq.{project_id}"},
            json={"milestones": milestones},
            headers=_hdrs(),
        )

    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail="Failed to add milestone.")

    return new_milestone


@router.put(
    "/{project_id}/milestones/{milestone_id}",
    summary="Update a milestone (CSR Head or PM)",
)
async def update_milestone(
    project_id: str,
    milestone_id: str,
    body: MilestoneUpdate,
    user: UserInfo = Depends(require_role("csr_head", "project_manager")),
):
    project = await _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _check_project_access(project, user)

    milestones: List[Dict] = project.get("milestones") or []
    target = next((m for m in milestones if m.get("milestone_id") == milestone_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Milestone not found.")

    for field, val in body.dict(exclude_none=True).items():
        target[field] = val

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.patch(
            f"{_sb_url()}/rest/v1/csr_projects",
            params={"project_id": f"eq.{project_id}"},
            json={"milestones": milestones},
            headers=_hdrs(),
        )

    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail="Failed to update milestone.")

    return target


@router.get("/{project_id}/history", summary="Stage transition history")
async def get_history(
    project_id: str,
    user: UserInfo = Depends(require_role("csr_head", "approver")),
):
    project = await _fetch_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    _check_project_access(project, user)
    return project.get("stage_history") or []


def register_csr_routes(app):
    app.include_router(router)
