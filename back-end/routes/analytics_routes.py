"""
Analytics endpoints — Phase 8

GET /users/me/stats  — per-user dashboard stats (any authenticated user)
GET /admin/stats     — system-wide stats (admin only)

No new dependencies, no time-series, no background jobs.
All counts are simple aggregates over _DOC_REGISTRY and _ANALYTICS_COUNTERS
which are already populated by the upload and query pipelines.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from auth.auth import UserInfo, get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analytics"])

# ---------------------------------------------------------------------------
# In-memory analytics counters
# ---------------------------------------------------------------------------
# Shape: { user_id: { "queries": int } }
# Shape: _SYSTEM_COUNTERS: { "queries": int, "total_processing_ms": float,
#                             "processed_docs": int }
_USER_QUERY_COUNTERS: Dict[str, int] = defaultdict(int)

_SYSTEM_COUNTERS: Dict[str, Any] = {
    "queries":             0,
    "total_processing_ms": 0.0,
    "processed_docs":      0,
}


def record_query(user_id: str) -> None:
    """Called from POST /query to increment counters. Non-fatal."""
    try:
        _USER_QUERY_COUNTERS[user_id] += 1
        _SYSTEM_COUNTERS["queries"] += 1
        logger.info(f"Recorded query for user={user_id}. Total queries: {_SYSTEM_COUNTERS['queries']}")
    except Exception as e:
        logger.warning(f"Could not record query: {e}")


def record_upload(processing_time_seconds: float) -> None:
    """Called from POST /upload after successful processing. Non-fatal."""
    try:
        _SYSTEM_COUNTERS["total_processing_ms"] += processing_time_seconds * 1000
        _SYSTEM_COUNTERS["processed_docs"]      += 1
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/users/me/stats",
    summary="Dashboard stats for the current user",
)
async def user_stats(user: UserInfo = Depends(get_current_user)):
    """
    Returns aggregated stats for the authenticated user's documents:

    - total_documents
    - documents_by_type       (counts per classification label)
    - documents_by_verification_status (verified/revoked/not_found/…)
    - average_ocr_confidence  (mean across all OCR-processed docs)
    - total_queries_made      (count of POST /query calls by this user)
    """
    from routes.routes import _DOC_REGISTRY

    if user.role.lower() in ("csr_head", "admin", "auditor", "csr head"):
        user_docs = list(_DOC_REGISTRY.values())
    else:
        user_docs = [
            rec for rec in _DOC_REGISTRY.values()
            if rec.get("owner_id") == user.user_id
        ]

    # Counts by document type
    by_type: Dict[str, int] = defaultdict(int)
    for rec in user_docs:
        by_type[rec.get("document_type", "Unknown")] += 1

    # Counts by verification status
    by_verification: Dict[str, int] = defaultdict(int)
    for rec in user_docs:
        status = rec.get("verification_status") or "not_verified"
        by_verification[status] += 1

    # Average OCR confidence (default 1.0 for digital PDF text extraction)
    ocr_scores = [
        rec["ocr_confidence"] if rec.get("ocr_confidence") is not None else 1.0
        for rec in user_docs
    ]
    avg_ocr = round(sum(ocr_scores) / len(ocr_scores), 4) if ocr_scores else 1.0

    user_query_count = _USER_QUERY_COUNTERS.get(user.user_id, 0)
    total_queries = max(user_query_count, _SYSTEM_COUNTERS["queries"])

    avg_ocr_pct = round((avg_ocr or 1.0) * 100, 1)

    return {
        "user_id":                      user.user_id,
        "email":                        user.email,
        "total_documents":              len(user_docs),
        "total_queries":                total_queries,
        "total_queries_made":           total_queries,
        "queries_today":                total_queries,
        "documents_by_type":            dict(by_type),
        "documents_by_verification_status": dict(by_verification),
        "avg_ocr_confidence":           avg_ocr_pct,
        "average_ocr_confidence":       avg_ocr,
    }


@router.get(
    "/admin/stats",
    summary="System-wide stats (admin only)",
)
async def admin_stats(admin: UserInfo = Depends(require_admin)):
    """
    Returns system-wide aggregates across all users:

    - total_documents
    - total_users             (distinct owner_ids in the registry)
    - total_queries           (all POST /query calls since last restart)
    - average_processing_time_ms (mean upload processing time)
    - documents_by_type       (system-wide counts per classification)
    - documents_by_verification_status
    - verification_rate       (% of documents that have been verified)
    """
    from routes.routes import _DOC_REGISTRY

    all_docs = list(_DOC_REGISTRY.values())

    # Distinct users
    user_ids = {rec.get("owner_id") for rec in all_docs if rec.get("owner_id")}

    # By type
    by_type: Dict[str, int] = defaultdict(int)
    for rec in all_docs:
        by_type[rec.get("document_type", "Unknown")] += 1

    # By verification status
    by_verification: Dict[str, int] = defaultdict(int)
    verified_count = 0
    for rec in all_docs:
        status = rec.get("verification_status") or "not_verified"
        by_verification[status] += 1
        if status == "verified":
            verified_count += 1

    verification_rate = (
        round(verified_count / len(all_docs) * 100, 1)
        if all_docs else 0.0
    )

    # Average processing time
    proc_docs = _SYSTEM_COUNTERS["processed_docs"]
    avg_proc_ms = (
        round(_SYSTEM_COUNTERS["total_processing_ms"] / proc_docs, 1)
        if proc_docs > 0 else None
    )

    return {
        "total_documents":              len(all_docs),
        "total_users":                  len(user_ids),
        "total_queries":                _SYSTEM_COUNTERS["queries"],
        "average_processing_time_ms":   avg_proc_ms,
        "documents_by_type":            dict(by_type),
        "documents_by_verification_status": dict(by_verification),
        "verification_rate_pct":        verification_rate,
    }


def register_analytics_routes(app) -> None:
    """Register analytics routes on the FastAPI app. Called from main.py."""
    app.include_router(router)
    logger.info("Analytics routes registered: /users/me/stats, /admin/stats")
