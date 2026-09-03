"""
CSR Project Service Layer
Feature #1: CSR Project Lifecycle Management

Coordinates project CRUD, lifecycle transitions, document linking, and audit logging.
"""

import datetime
import uuid
from typing import Any, Dict, List, Optional, Set
from fastapi import HTTPException, status

from project.models import (
    CSRProject,
    ProjectAuditEntry,
    ProjectCreateRequest,
    ProjectStage,
    ProjectUpdateRequest,
    StageHistoryEntry,
)
from project.lifecycle import (
    get_allowed_transitions,
    validate_transition_or_raise,
    validate_update_fields_or_raise,
)
from project.audit import (
    ACTION_PROJECT_CREATED,
    ACTION_PROJECT_UPDATED,
    ACTION_PROJECT_STAGE_CHANGED,
    ACTION_PROJECT_DOCUMENT_LINKED,
    ACTION_PROJECT_DOCUMENT_UNLINKED,
    create_audit_entry,
)
from project.storage import project_store, ProjectStore


class ProjectService:
    """Service layer managing CSR project domain logic."""

    def __init__(self, store: Optional[ProjectStore] = None):
        self.store = store or project_store

    def _now(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _generate_project_code(self) -> str:
        year = datetime.datetime.now(datetime.timezone.utc).year
        seq = self.store.get_next_sequence_for_year(year)
        return f"CSR-{year}-{seq:05d}"

    def create_project(self, req: ProjectCreateRequest, user_id: str) -> CSRProject:
        """Create a new CSR project in DRAFT stage."""
        now = self._now()
        project_id = str(uuid.uuid4())
        project_code = self._generate_project_code()

        initial_history = [
            StageHistoryEntry(
                from_stage=None,
                to_stage=ProjectStage.DRAFT,
                changed_at=now,
                changed_by=user_id,
                comments="Initial project creation in DRAFT",
            )
        ]

        project = CSRProject(
            project_id=project_id,
            project_code=project_code,
            title=req.title.strip(),
            description=req.description.strip(),
            organization_name=req.organization_name.strip(),
            sector=req.sector.strip(),
            budget=req.budget,
            currency=req.currency.strip().upper(),
            location=req.location.strip() if req.location else None,
            current_stage=ProjectStage.DRAFT,
            stage_history=initial_history,
            linked_document_ids=[],
            owner_id=user_id,
            created_at=now,
            updated_at=now,
        )

        saved = self.store.create(project)

        # Record audit event
        audit_entry = create_audit_entry(
            project_id=project_id,
            action=ACTION_PROJECT_CREATED,
            performed_by=user_id,
            details={
                "project_code": project_code,
                "title": project.title,
                "organization_name": project.organization_name,
                "sector": project.sector,
                "budget": project.budget,
                "currency": project.currency,
                "initial_stage": ProjectStage.DRAFT.value,
            },
        )
        self.store.add_audit_entry(audit_entry)

        return saved

    def get_project(self, project_id: str, user_id: str, is_admin: bool = False) -> CSRProject:
        """Retrieve project by ID, verifying access."""
        project = self.store.get(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "project_not_found", "message": f"Project '{project_id}' not found."},
            )
        if not is_admin and project.owner_id != user_id:
            # Mask existence on unauthorized access per repo pattern
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "project_not_found", "message": f"Project '{project_id}' not found."},
            )
        return project

    def list_projects(
        self,
        user_id: str,
        stage: Optional[ProjectStage] = None,
        is_admin: bool = False,
    ) -> List[CSRProject]:
        """List projects for the user."""
        owner_filter = None if is_admin else user_id
        return self.store.list_projects(owner_id=owner_filter, stage=stage)

    def update_project(
        self,
        project_id: str,
        req: ProjectUpdateRequest,
        user_id: str,
        is_admin: bool = False,
    ) -> CSRProject:
        """Update project fields with stage-based validation."""
        project = self.get_project(project_id, user_id, is_admin)

        # Find which fields were provided in the request
        update_data = req.model_dump(exclude_unset=True)
        if not update_data:
            return project

        # Validate that requested fields are allowed in current stage
        requested_fields: Set[str] = set(update_data.keys())
        validate_update_fields_or_raise(project.current_stage, requested_fields)

        # Apply updates
        for key, value in update_data.items():
            if value is not None:
                if isinstance(value, str):
                    value = value.strip()
                setattr(project, key, value)

        now = self._now()
        project.updated_at = now
        saved = self.store.update(project)

        # Record audit event
        audit_entry = create_audit_entry(
            project_id=project_id,
            action=ACTION_PROJECT_UPDATED,
            performed_by=user_id,
            details={"updated_fields": list(update_data.keys())},
        )
        self.store.add_audit_entry(audit_entry)

        return saved

    def transition_stage(
        self,
        project_id: str,
        target_stage: ProjectStage,
        comments: Optional[str],
        user_id: str,
        is_admin: bool = False,
    ) -> CSRProject:
        """Transition project to target lifecycle stage."""
        project = self.get_project(project_id, user_id, is_admin)
        from_stage = project.current_stage

        # Validate transition against state machine matrix
        validate_transition_or_raise(from_stage, target_stage)

        now = self._now()
        history_entry = StageHistoryEntry(
            from_stage=from_stage,
            to_stage=target_stage,
            changed_at=now,
            changed_by=user_id,
            comments=comments.strip() if comments else None,
        )

        project.current_stage = target_stage
        project.stage_history.append(history_entry)
        project.updated_at = now

        saved = self.store.update(project)

        # Record audit event
        audit_entry = create_audit_entry(
            project_id=project_id,
            action=ACTION_PROJECT_STAGE_CHANGED,
            performed_by=user_id,
            details={
                "from_stage": from_stage.value,
                "to_stage": target_stage.value,
                "comments": comments,
            },
        )
        self.store.add_audit_entry(audit_entry)

        return saved

    def get_allowed_stages(
        self,
        project_id: str,
        user_id: str,
        is_admin: bool = False,
    ) -> List[ProjectStage]:
        """Get legal next stages for project."""
        project = self.get_project(project_id, user_id, is_admin)
        return get_allowed_transitions(project.current_stage)

    def _verify_document_exists_and_accessible(
        self,
        document_id: str,
        user_id: str,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Verify document exists in system and belongs to user.
        Integrates with existing document registry and FAISS store.
        """
        from routes.routes import _DOC_REGISTRY

        doc = _DOC_REGISTRY.get(document_id)
        if doc is not None:
            if not is_admin and doc.get("owner_id") != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": "document_not_found", "message": f"Document '{document_id}' not found."},
                )
            return doc

        # Fallback to FAISS chunk metadata if not in registry
        try:
            from main import rag_engine
            vdb = getattr(rag_engine, "vector_db", None) if rag_engine else None
            if vdb and hasattr(vdb, "documents"):
                chunks = [
                    c for c in vdb.documents.values()
                    if c.metadata.get("document_id") == document_id
                ]
                if chunks:
                    meta = chunks[0].metadata
                    if not is_admin and meta.get("owner_id") != user_id:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail={"error": "document_not_found", "message": f"Document '{document_id}' not found."},
                        )
                    return {
                        "document_id": document_id,
                        "filename": meta.get("source", meta.get("filename", "unknown")),
                        "document_type": meta.get("document_type", "Unknown"),
                        "status": "COMPLETED",
                        "owner_id": meta.get("owner_id", ""),
                    }
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "document_not_found", "message": f"Document '{document_id}' does not exist in the system."},
        )

    def link_document(
        self,
        project_id: str,
        document_id: str,
        user_id: str,
        is_admin: bool = False,
    ) -> CSRProject:
        """Associate an existing document with the project."""
        project = self.get_project(project_id, user_id, is_admin)

        # Validate that document exists in the system and user has access
        self._verify_document_exists_and_accessible(document_id, user_id, is_admin)

        if document_id in project.linked_document_ids:
            return project  # Already linked

        project.linked_document_ids.append(document_id)
        now = self._now()
        project.updated_at = now
        saved = self.store.update(project)

        # Record audit event
        audit_entry = create_audit_entry(
            project_id=project_id,
            action=ACTION_PROJECT_DOCUMENT_LINKED,
            performed_by=user_id,
            details={"document_id": document_id},
        )
        self.store.add_audit_entry(audit_entry)

        return saved

    def unlink_document(
        self,
        project_id: str,
        document_id: str,
        user_id: str,
        is_admin: bool = False,
    ) -> CSRProject:
        """Remove document association from the project."""
        project = self.get_project(project_id, user_id, is_admin)

        if document_id not in project.linked_document_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "document_not_linked", "message": f"Document '{document_id}' is not linked to this project."},
            )

        project.linked_document_ids.remove(document_id)
        now = self._now()
        project.updated_at = now
        saved = self.store.update(project)

        # Record audit event
        audit_entry = create_audit_entry(
            project_id=project_id,
            action=ACTION_PROJECT_DOCUMENT_UNLINKED,
            performed_by=user_id,
            details={"document_id": document_id},
        )
        self.store.add_audit_entry(audit_entry)

        return saved

    def get_linked_documents(
        self,
        project_id: str,
        user_id: str,
        is_admin: bool = False,
    ) -> List[Dict[str, Any]]:
        """List metadata for all documents linked to the project."""
        project = self.get_project(project_id, user_id, is_admin)
        from routes.routes import _DOC_REGISTRY

        results = []
        for did in project.linked_document_ids:
            reg = _DOC_REGISTRY.get(did)
            if reg:
                results.append({
                    "document_id": did,
                    "filename": reg.get("filename", "unknown"),
                    "document_type": reg.get("document_type", "Unknown"),
                    "status": reg.get("status", "COMPLETED"),
                    "upload_date": reg.get("upload_date"),
                    "ocr_confidence": reg.get("ocr_confidence"),
                    "verification_status": reg.get("verification_status"),
                })
            else:
                results.append({
                    "document_id": did,
                    "filename": "Unknown document",
                    "document_type": "Unknown",
                    "status": "COMPLETED",
                    "upload_date": None,
                    "ocr_confidence": None,
                    "verification_status": None,
                })
        return results

    def get_audit_trail(
        self,
        project_id: str,
        user_id: str,
        is_admin: bool = False,
    ) -> List[ProjectAuditEntry]:
        """Retrieve audit history for project."""
        self.get_project(project_id, user_id, is_admin)
        return self.store.get_audit_trail(project_id)


# Singleton service instance
project_service = ProjectService()
