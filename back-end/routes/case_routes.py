"""
CSR Case Management and Completeness API Routes.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel

from auth.auth import get_current_user, UserInfo
from routes.routes import _DOC_REGISTRY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cases", tags=["cases"])

# In-memory Case Registry for cases
# Shape: { case_id: { case_id, title, owner_id, document_ids: [...] } }
_CASE_REGISTRY: Dict[str, Dict[str, Any]] = {}

REQUIRED_CSR_DOCUMENTS = [
    "Project Proposal",
    "Budget Sheet",
    "Utilization Certificate",
    "Completion Report",
]

OPTIONAL_CSR_DOCUMENTS = [
    "Progress Report",
    "Compliance Certificate",
    "Partnership Agreement",
    "Audit Report",
    "Impact Assessment Report",
    "CSR Policy Document",
]


class CaseCreateInput(BaseModel):
    case_id: str
    title: Optional[str] = None
    document_ids: Optional[List[str]] = None


@router.post("", summary="Create or register a CSR case")
async def create_case(
    data: CaseCreateInput,
    user: UserInfo = Depends(get_current_user),
):
    if user.role == "auditor":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "message": "Auditor role cannot create new projects. Only CSR Head or Project Manager can create projects.",
            },
        )

    case_id = data.case_id
    doc_ids = data.document_ids or []

    _CASE_REGISTRY[case_id] = {
        "case_id": case_id,
        "title": data.title or f"Case {case_id}",
        "owner_id": user.user_id,
        "document_ids": doc_ids,
    }

    # Associate document IDs in registry
    for did in doc_ids:
        if did in _DOC_REGISTRY:
            _DOC_REGISTRY[did]["case_id"] = case_id

    return {
        "status": "success",
        "case_id": case_id,
        "document_count": len(doc_ids),
    }


@router.get("/{case_id}/csr-completeness", summary="Get CSR case completeness breakdown")
async def get_csr_completeness(
    case_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """
    Evaluates CSR document completeness for a given case.
    Required CSR documents: Project Proposal, Budget Sheet, Utilization Certificate, Completion Report.
    Optional CSR documents: Progress Report, Compliance Certificate, Partnership Agreement, Audit Report, Impact Assessment Report, CSR Policy Document.
    """
    case_entry = _CASE_REGISTRY.get(case_id)

    # Collect documents linked to this case_id
    case_docs = []

    # 1. Documents explicitly registered in _CASE_REGISTRY
    if case_entry:
        if case_entry.get("owner_id") != user.user_id:
            raise HTTPException(
                status_code=404,
                detail={"error": "Case not found or access denied", "case_id": case_id},
            )
        for did in case_entry.get("document_ids", []):
            doc = _DOC_REGISTRY.get(did)
            if doc and doc.get("owner_id") == user.user_id:
                case_docs.append(doc)

    # 2. Documents in _DOC_REGISTRY marked with case_id
    for doc in _DOC_REGISTRY.values():
        if doc.get("case_id") == case_id and doc.get("owner_id") == user.user_id:
            if doc not in case_docs:
                case_docs.append(doc)

    # If no case entry and no linked documents found for user
    if not case_entry and not case_docs:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found or access denied", "case_id": case_id},
        )

    # Gather unique document types present in case
    present_types = {d.get("document_type") for d in case_docs if d.get("document_type")}

    # Calculate required & optional completeness
    required_present = [dt for dt in REQUIRED_CSR_DOCUMENTS if dt in present_types]
    required_missing = [dt for dt in REQUIRED_CSR_DOCUMENTS if dt not in present_types]
    optional_present = [dt for dt in OPTIONAL_CSR_DOCUMENTS if dt in present_types]

    score = round(len(required_present) / len(REQUIRED_CSR_DOCUMENTS), 2)
    is_complete = (len(required_missing) == 0)

    return {
        "case_id": case_id,
        "required_present": required_present,
        "required_missing": required_missing,
        "optional_present": optional_present,
        "completeness_score": score,
        "is_complete": is_complete,
    }


def register_case_routes(app: FastAPI) -> None:
    """Register case router on FastAPI app instance."""
    app.include_router(router)
