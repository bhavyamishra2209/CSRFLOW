"""
CSR Project Lifecycle State Machine
Feature #1: CSR Project Lifecycle Management

Pure state machine defining valid/invalid stage transitions and editability rules.
Independent from HTTP route handling.
"""

from typing import Dict, List, Set
from fastapi import HTTPException, status
from project.models import ProjectStage


# ---------------------------------------------------------------------------
# Approved Transition Matrix
# ---------------------------------------------------------------------------

TRANSITION_MATRIX: Dict[ProjectStage, Set[ProjectStage]] = {
    ProjectStage.DRAFT: {
        ProjectStage.SUBMITTED,
        ProjectStage.CLOSED,
    },
    ProjectStage.SUBMITTED: {
        ProjectStage.UNDER_EVALUATION,
        ProjectStage.DRAFT,
    },
    ProjectStage.UNDER_EVALUATION: {
        ProjectStage.APPROVED,
        ProjectStage.DRAFT,
        ProjectStage.CLOSED,
    },
    ProjectStage.APPROVED: {
        ProjectStage.FUNDED,
        ProjectStage.UNDER_EVALUATION,
    },
    ProjectStage.FUNDED: {
        ProjectStage.IN_PROGRESS,
    },
    ProjectStage.IN_PROGRESS: {
        ProjectStage.UNDER_REVIEW,
        ProjectStage.CLOSED,
    },
    ProjectStage.UNDER_REVIEW: {
        ProjectStage.COMPLETED,
        ProjectStage.IN_PROGRESS,
    },
    ProjectStage.COMPLETED: {
        ProjectStage.CLOSED,
    },
    ProjectStage.CLOSED: set(),  # Terminal state
}


# ---------------------------------------------------------------------------
# Field Editability by Lifecycle Stage
# ---------------------------------------------------------------------------

ALL_METADATA_FIELDS = {
    "title",
    "description",
    "organization_name",
    "sector",
    "budget",
    "currency",
    "location",
}

RESTRICTED_METADATA_FIELDS = {
    "description",
    "location",
}


def get_allowed_transitions(current_stage: ProjectStage) -> List[ProjectStage]:
    """Return list of legal stages that can follow the current stage."""
    return sorted(list(TRANSITION_MATRIX.get(current_stage, set())), key=lambda s: s.value)


def is_valid_transition(current_stage: ProjectStage, target_stage: ProjectStage) -> bool:
    """Check if transitioning from current_stage to target_stage is allowed."""
    allowed = TRANSITION_MATRIX.get(current_stage, set())
    return target_stage in allowed


def validate_transition_or_raise(current_stage: ProjectStage, target_stage: ProjectStage) -> None:
    """
    Validate transition and raise HTTP 400 with human-readable detail if invalid.
    """
    if current_stage == ProjectStage.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "terminal_stage",
                "message": "Project is CLOSED. No further stage transitions are permitted.",
                "current_stage": current_stage.value,
            },
        )

    if not is_valid_transition(current_stage, target_stage):
        allowed = [s.value for s in get_allowed_transitions(current_stage)]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_stage_transition",
                "message": f"Cannot transition project from '{current_stage.value}' to '{target_stage.value}'.",
                "current_stage": current_stage.value,
                "target_stage": target_stage.value,
                "allowed_next_stages": allowed,
            },
        )


def get_editable_fields(current_stage: ProjectStage) -> Set[str]:
    """
    Returns the set of fields allowed to be updated in the given stage:
    - DRAFT: all fields editable
    - SUBMITTED / UNDER_EVALUATION: locked for evaluation (empty)
    - APPROVED / FUNDED / IN_PROGRESS / UNDER_REVIEW: restricted fields only
    - COMPLETED / CLOSED: read-only (empty)
    """
    if current_stage == ProjectStage.DRAFT:
        return ALL_METADATA_FIELDS
    elif current_stage in (ProjectStage.SUBMITTED, ProjectStage.UNDER_EVALUATION):
        return set()
    elif current_stage in (
        ProjectStage.APPROVED,
        ProjectStage.FUNDED,
        ProjectStage.IN_PROGRESS,
        ProjectStage.UNDER_REVIEW,
    ):
        return RESTRICTED_METADATA_FIELDS
    else:  # COMPLETED, CLOSED
        return set()


def validate_update_fields_or_raise(current_stage: ProjectStage, requested_fields: Set[str]) -> None:
    """
    Validate that the requested update fields are permitted in the project's current stage.
    """
    editable = get_editable_fields(current_stage)
    forbidden = requested_fields - editable

    if current_stage in (ProjectStage.COMPLETED, ProjectStage.CLOSED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "project_locked",
                "message": f"Project in stage '{current_stage.value}' is read-only and cannot be updated.",
                "current_stage": current_stage.value,
            },
        )

    if current_stage in (ProjectStage.SUBMITTED, ProjectStage.UNDER_EVALUATION):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "project_under_review",
                "message": f"Project is '{current_stage.value}' and locked for evaluation. Return project to DRAFT to modify metadata.",
                "current_stage": current_stage.value,
            },
        )

    if forbidden:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "field_update_restricted",
                "message": f"Fields {sorted(list(forbidden))} cannot be updated while project is in '{current_stage.value}'.",
                "current_stage": current_stage.value,
                "allowed_editable_fields": sorted(list(editable)),
            },
        )
