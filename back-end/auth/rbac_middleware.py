"""
Role-Based Access Control (RBAC) Middleware & Permission Dependencies.

Supports 3 enterprise CSR roles:
1. CSR Head (Programme Owner / Admin)
2. Project Manager (Execution)
3. Approver / Auditor (Independent Reviewer)
"""

import logging
from enum import Enum
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status

from auth.auth import get_current_user, UserInfo
from routes.case_routes import _CASE_REGISTRY

logger = logging.getLogger(__name__)


class RoleEnum(str, Enum):
    CSR_HEAD = "csr_head"
    PROJECT_MANAGER = "project_manager"
    AUDITOR = "auditor"


def require_csr_head(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Dependency: Requires CSR Head (Admin/Programme Owner) role."""
    if user.role in ("csr_head", "admin", "service_role"):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "forbidden",
            "message": "Only CSR Head / Admin can perform this action.",
        },
    )


def require_project_manager(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Dependency: Requires Project Manager or CSR Head role."""
    if user.role in ("project_manager", "pm", "csr_head", "admin", "service_role"):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "forbidden",
            "message": "Project Manager or CSR Head role required for execution actions.",
        },
    )


def require_auditor_role(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Dependency: Requires Approver / Auditor role."""
    if user.role in ("auditor", "approver", "csr_head", "admin", "service_role"):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "forbidden",
            "message": "Approver / Auditor role required for review actions.",
        },
    )


def verify_pm_case_access(case_id: str, user: UserInfo) -> Dict[str, Any]:
    """Verify that Project Manager has access to this case."""
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    # CSR Head / Admin can access all cases
    if user.role in ("csr_head", "admin", "service_role"):
        return case

    assigned_pm = case.get("assigned_pm_id")
    if assigned_pm and assigned_pm != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "access_denied",
                "message": f"Project Manager '{user.user_id}' is not assigned to project '{case_id}'. Cannot view or edit unassigned projects.",
            },
        )

    return case


def verify_auditor_case_access(case_id: str, user: UserInfo) -> Dict[str, Any]:
    """Verify that Auditor has access to this review case."""
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    # CSR Head / Admin can access all cases
    if user.role in ("csr_head", "admin", "service_role"):
        return case

    assigned_auditor = case.get("assigned_auditor_id")
    if assigned_auditor and assigned_auditor != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "access_denied",
                "message": f"Auditor '{user.user_id}' is not assigned to project '{case_id}'. Cannot review unassigned projects.",
            },
        )

    return case


def enforce_separation_of_duties(creator_id: Optional[str], reviewer_id: str) -> None:
    """Enforce separation of duties: Creator cannot approve their own project."""
    if creator_id and creator_id == reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "separation_of_duties_violation",
                "message": "Separation of Duties Violation: You cannot approve or reject a project you created.",
            },
        )
