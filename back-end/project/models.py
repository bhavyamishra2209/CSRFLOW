"""
CSR Project Lifecycle Management - Data Models & Schemas
Feature #1: CSR Project Lifecycle Management
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectStage(str, Enum):
    """CSR project lifecycle stages (9 sequential/return stages)."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_EVALUATION = "UNDER_EVALUATION"
    APPROVED = "APPROVED"
    FUNDED = "FUNDED"
    IN_PROGRESS = "IN_PROGRESS"
    UNDER_REVIEW = "UNDER_REVIEW"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class StageHistoryEntry(BaseModel):
    """Record of a stage transition."""
    from_stage: Optional[ProjectStage] = None
    to_stage: ProjectStage
    changed_at: str
    changed_by: str
    comments: Optional[str] = None


class ProjectAuditEntry(BaseModel):
    """Audit trail record for a project lifecycle action."""
    audit_id: str
    project_id: str
    action: str
    performed_by: str
    performed_at: str
    details: Dict[str, Any] = Field(default_factory=dict)


class CSRProject(BaseModel):
    """CSR Project entity."""
    project_id: str
    project_code: str
    title: str
    description: str = ""
    organization_name: str
    sector: str
    budget: float = 0.0
    currency: str = "INR"
    location: Optional[str] = None
    current_stage: ProjectStage = ProjectStage.DRAFT
    stage_history: List[StageHistoryEntry] = Field(default_factory=list)
    linked_document_ids: List[str] = Field(default_factory=list)
    owner_id: str
    created_at: str
    updated_at: str


class ProjectCreateRequest(BaseModel):
    """Payload to create a new project."""
    title: str = Field(..., min_length=1, description="Project title")
    organization_name: str = Field(..., min_length=1, description="Target NGO or partner organization")
    sector: str = Field(..., min_length=1, description="Focus sector (e.g., Education, Healthcare)")
    budget: float = Field(default=0.0, ge=0.0, description="Project budget")
    currency: str = Field(default="INR", description="Currency code (e.g., INR, USD)")
    description: str = Field(default="", description="Detailed project description")
    location: Optional[str] = Field(default=None, description="Project geographical location / state / district")


class ProjectUpdateRequest(BaseModel):
    """Payload to update an existing project."""
    title: Optional[str] = None
    description: Optional[str] = None
    organization_name: Optional[str] = None
    sector: Optional[str] = None
    budget: Optional[float] = None
    currency: Optional[str] = None
    location: Optional[str] = None


class StageTransitionRequest(BaseModel):
    """Payload to request a lifecycle stage transition."""
    target_stage: ProjectStage = Field(..., description="Target lifecycle stage")
    comments: Optional[str] = Field(default=None, description="Optional comments or transition rationale")


class LinkDocumentRequest(BaseModel):
    """Payload to link an existing document to a project."""
    document_id: str = Field(..., min_length=1, description="Existing document UUID")
