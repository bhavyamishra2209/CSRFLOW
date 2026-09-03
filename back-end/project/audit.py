"""
CSR Project Audit Trail
Feature #1: CSR Project Lifecycle Management

Records and provides audit trail events for project lifecycle actions.
"""

import datetime
import uuid
from typing import Any, Dict
from project.models import ProjectAuditEntry


# Event Types Constants
ACTION_PROJECT_CREATED = "PROJECT_CREATED"
ACTION_PROJECT_UPDATED = "PROJECT_UPDATED"
ACTION_PROJECT_STAGE_CHANGED = "PROJECT_STAGE_CHANGED"
ACTION_PROJECT_DOCUMENT_LINKED = "PROJECT_DOCUMENT_LINKED"
ACTION_PROJECT_DOCUMENT_UNLINKED = "PROJECT_DOCUMENT_UNLINKED"


def create_audit_entry(
    project_id: str,
    action: str,
    performed_by: str,
    details: Dict[str, Any] = None,
) -> ProjectAuditEntry:
    """Create a standardized audit entry record."""
    return ProjectAuditEntry(
        audit_id=str(uuid.uuid4()),
        project_id=project_id,
        action=action,
        performed_by=performed_by,
        performed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        details=details or {},
    )
