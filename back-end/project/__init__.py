"""
CSR Project Lifecycle Management Package
Feature #1: CSR Project Lifecycle Management
"""

from project.models import (
    ProjectStage,
    CSRProject,
    StageHistoryEntry,
    ProjectAuditEntry,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    StageTransitionRequest,
    LinkDocumentRequest,
)
from project.lifecycle import (
    get_allowed_transitions,
    is_valid_transition,
    validate_transition_or_raise,
)
from project.storage import project_store, ProjectStore
from project.service import project_service, ProjectService

__all__ = [
    "ProjectStage",
    "CSRProject",
    "StageHistoryEntry",
    "ProjectAuditEntry",
    "ProjectCreateRequest",
    "ProjectUpdateRequest",
    "StageTransitionRequest",
    "LinkDocumentRequest",
    "get_allowed_transitions",
    "is_valid_transition",
    "validate_transition_or_raise",
    "project_store",
    "ProjectStore",
    "project_service",
    "ProjectService",
]
