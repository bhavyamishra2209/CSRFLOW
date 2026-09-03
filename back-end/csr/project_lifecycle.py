"""
CSR Project lifecycle — stages, models, transition logic.

Workflow:
  draft → submitted → under_review → approved / rejected → in_progress
  → monitoring → completed → closed

  rejected → draft  (allow re-submission)

Role gates on transitions:
  draft → submitted        : project_manager or csr_head
  submitted → under_review : approver
  under_review → approved  : approver  (cannot be the project creator)
  under_review → rejected  : approver  (cannot be the project creator)
  approved → in_progress   : csr_head or project_manager
  in_progress → monitoring : project_manager or csr_head
  monitoring → completed   : approver
  completed → closed       : csr_head
  rejected → draft         : project_manager or csr_head
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (plain str so they survive JSON serialisation easily)
# ---------------------------------------------------------------------------

class ProjectStage:
    DRAFT        = "draft"
    SUBMITTED    = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED     = "approved"
    REJECTED     = "rejected"
    IN_PROGRESS  = "in_progress"
    MONITORING   = "monitoring"
    COMPLETED    = "completed"
    CLOSED       = "closed"

    ALL = [
        DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED,
        REJECTED, IN_PROGRESS, MONITORING, COMPLETED, CLOSED,
    ]

    LABELS = {
        DRAFT:        "Draft",
        SUBMITTED:    "Submitted",
        UNDER_REVIEW: "Under Review",
        APPROVED:     "Approved",
        REJECTED:     "Rejected",
        IN_PROGRESS:  "In Progress",
        MONITORING:   "Monitoring",
        COMPLETED:    "Completed",
        CLOSED:       "Closed",
    }


class ProjectDomain:
    EDUCATION        = "education"
    HEALTHCARE       = "healthcare"
    ENVIRONMENT      = "environment"
    COMMUNITY        = "community"
    LIVELIHOOD       = "livelihood"
    WATER_SANITATION = "water_sanitation"
    DISASTER_RELIEF  = "disaster_relief"
    OTHER            = "other"

    ALL = [
        EDUCATION, HEALTHCARE, ENVIRONMENT, COMMUNITY,
        LIVELIHOOD, WATER_SANITATION, DISASTER_RELIEF, OTHER,
    ]


# ---------------------------------------------------------------------------
# Transition table: {from_stage: [(to_stage, allowed_roles)]}
# ---------------------------------------------------------------------------

_TRANSITIONS: Dict[str, List[tuple]] = {
    ProjectStage.DRAFT:        [(ProjectStage.SUBMITTED,    {"project_manager", "csr_head"})],
    ProjectStage.SUBMITTED:    [(ProjectStage.UNDER_REVIEW, {"approver"}),
                                (ProjectStage.REJECTED,     {"approver"})],
    ProjectStage.UNDER_REVIEW: [(ProjectStage.APPROVED,     {"approver"}),
                                (ProjectStage.REJECTED,     {"approver"})],
    ProjectStage.APPROVED:     [(ProjectStage.IN_PROGRESS,  {"csr_head", "project_manager"})],
    ProjectStage.REJECTED:     [(ProjectStage.DRAFT,        {"project_manager", "csr_head"})],
    ProjectStage.IN_PROGRESS:  [(ProjectStage.MONITORING,   {"project_manager", "csr_head"})],
    ProjectStage.MONITORING:   [(ProjectStage.COMPLETED,    {"approver"})],
    ProjectStage.COMPLETED:    [(ProjectStage.CLOSED,       {"csr_head"})],
    ProjectStage.CLOSED:       [],
}


def validate_stage_transition(
    current: str,
    requested: str,
    actor_role: Optional[str],
    actor_id: Optional[str] = None,
    project_creator_id: Optional[str] = None,
) -> None:
    """
    Raises ValueError if the transition is not allowed.

    Special rule: an approver cannot approve/reject a project they created.
    (Enforced when actor_role == 'approver' and actor_id == project_creator_id.)
    """
    transitions = _TRANSITIONS.get(current)
    if transitions is None:
        raise ValueError(f"Unknown stage: '{current}'")

    allowed_targets = {t[0]: t[1] for t in transitions}
    if requested not in allowed_targets:
        allowed_list = list(allowed_targets.keys()) or ["none"]
        raise ValueError(
            f"Cannot move from '{current}' to '{requested}'. "
            f"Allowed next stages: {allowed_list}."
        )

    required_roles = allowed_targets[requested]
    if actor_role not in required_roles:
        raise ValueError(
            f"Stage '{requested}' requires role: {' or '.join(required_roles)}. "
            f"Your role: {actor_role}."
        )

    # Approver self-approval guard
    approval_stages = {ProjectStage.APPROVED, ProjectStage.REJECTED, ProjectStage.COMPLETED}
    if (
        requested in approval_stages
        and actor_role == "approver"
        and actor_id
        and project_creator_id
        and actor_id == project_creator_id
    ):
        raise ValueError(
            "Approvers cannot approve or reject projects they created."
        )


# ---------------------------------------------------------------------------
# Pydantic schemas — request / response bodies
# ---------------------------------------------------------------------------

class MilestoneCreate(BaseModel):
    title:            str
    description:      str = ""
    target_date:      str = Field(..., description="ISO date YYYY-MM-DD")
    budget_allocated: float = Field(0.0, ge=0)
    deliverables:     List[str] = []


class MilestoneUpdate(BaseModel):
    title:            Optional[str] = None
    description:      Optional[str] = None
    target_date:      Optional[str] = None
    completion_date:  Optional[str] = None
    status:           Optional[str] = None   # pending|in_progress|completed|overdue
    budget_used:      Optional[float] = None
    deliverables:     Optional[List[str]] = None


class ProjectCreate(BaseModel):
    title:       str = Field(..., min_length=3, max_length=300)
    domain:      str = Field(..., description=f"One of: {ProjectDomain.ALL}")
    description: str = ""
    budget:      Optional[float] = Field(None, ge=0)
    milestones:  List[MilestoneCreate] = []


class ProjectUpdate(BaseModel):
    title:       Optional[str] = None
    domain:      Optional[str] = None
    description: Optional[str] = None
    budget:      Optional[float] = Field(None, ge=0)


class AssignMembers(BaseModel):
    assigned_pm:       Optional[str] = Field(None, description="user_id of the project_manager")
    assigned_approver: Optional[str] = Field(None, description="user_id of the approver")


class StageTransition(BaseModel):
    new_stage: str = Field(..., description=f"One of: {ProjectStage.ALL}")
    comment:   str = ""


class ProjectResponse(BaseModel):
    project_id:        str
    title:             str
    domain:            str
    description:       str
    budget:            Optional[float]
    stage:             str
    stage_label:       str
    created_by:        Optional[str]
    assigned_pm:       Optional[str]
    assigned_approver: Optional[str]
    created_at:        str
    updated_at:        str
    milestones:        List[Dict[str, Any]] = []
    documents:         List[Any] = []
    impact_data:       Dict[str, Any] = {}

    class Config:
        from_attributes = True
