"""
CSR Milestone & Timeline Tracking API Routes.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth.auth import get_current_user, UserInfo
from routes.case_routes import _CASE_REGISTRY
from milestones.milestone_tracker import MilestoneManager, MilestoneStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cases", tags=["CSR Milestone & Timeline Tracking"])


class MilestoneCreateInput(BaseModel):
    title: str = Field(description="Milestone title (e.g. Infrastructure Construction)")
    target_date: str = Field(description="Target completion date (YYYY-MM-DD)")
    description: Optional[str] = Field(default="", description="Milestone scope description")
    allocated_budget: Optional[float] = Field(default=0.0, description="Allocated budget for this milestone")
    target_beneficiaries: Optional[int] = Field(default=0, description="Target beneficiary count for this phase")
    milestone_id: Optional[str] = Field(default=None, description="Custom milestone ID (optional)")
    evidence_document_ids: Optional[List[str]] = Field(default=None, description="Linked evidence document IDs")


class MilestoneUpdateInput(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, description="PLANNED, IN_PROGRESS, COMPLETED, DELAYED, CANCELLED")
    target_date: Optional[str] = None
    completion_date: Optional[str] = None
    allocated_budget: Optional[float] = None
    spent_amount: Optional[float] = None
    progress_percentage: Optional[float] = Field(default=None, description="Progress 0.0 to 100.0")
    target_beneficiaries: Optional[int] = None
    achieved_beneficiaries: Optional[int] = None
    evidence_document_ids: Optional[List[str]] = None


@router.post("/{case_id}/milestones", summary="Create a project milestone for a CSR case")
async def create_milestone_endpoint(
    case_id: str,
    data: MilestoneCreateInput,
    user: UserInfo = Depends(get_current_user),
):
    """Create a new project milestone associated with a CSR case."""
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    try:
        ms = MilestoneManager.create_milestone(
            case_id=case_id,
            title=data.title,
            target_date=data.target_date,
            description=data.description or "",
            allocated_budget=data.allocated_budget or 0.0,
            target_beneficiaries=data.target_beneficiaries or 0,
            milestone_id=data.milestone_id,
            evidence_document_ids=data.evidence_document_ids,
        )
        return {
            "status": "success",
            "milestone": ms,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "milestone_creation_error", "message": str(e)},
        )


@router.get("/{case_id}/milestones", summary="List all milestones and overview for a CSR case")
async def list_case_milestones_endpoint(
    case_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Get all milestones and current progress overview for a CSR case."""
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    milestones = MilestoneManager.get_case_milestones(case_id)
    summary = MilestoneManager.get_timeline_summary(case_id)

    return {
        "case_id": case_id,
        "case_title": case.get("title"),
        "milestone_count": len(milestones),
        "summary": summary,
        "milestones": milestones,
    }


@router.get("/{case_id}/milestones/{milestone_id}", summary="Get specific milestone details")
async def get_milestone_endpoint(
    case_id: str,
    milestone_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Get details for a single project milestone."""
    ms = MilestoneManager.get_milestone(milestone_id)
    if ms is None or ms.get("case_id") != case_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "Milestone not found", "milestone_id": milestone_id},
        )
    return ms


@router.patch("/{case_id}/milestones/{milestone_id}", summary="Update milestone progress & deliverables")
async def update_milestone_endpoint(
    case_id: str,
    milestone_id: str,
    data: MilestoneUpdateInput,
    user: UserInfo = Depends(get_current_user),
):
    """Update milestone status, completion percentage, financial spend, or deliverables."""
    if user.role == "auditor":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "message": "Auditor role cannot edit milestone budgets or progress. Only Project Manager or CSR Head can update execution milestones.",
            },
        )

    ms = MilestoneManager.get_milestone(milestone_id)
    if ms is None or ms.get("case_id") != case_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "Milestone not found", "milestone_id": milestone_id},
        )

    updates = data.model_dump(exclude_unset=True)
    updated_ms = MilestoneManager.update_milestone(milestone_id, updates)
    
    summary = MilestoneManager.get_timeline_summary(case_id)

    return {
        "status": "success",
        "milestone": updated_ms,
        "updated_timeline_summary": summary,
    }


@router.delete("/{case_id}/milestones/{milestone_id}", summary="Delete a milestone")
async def delete_milestone_endpoint(
    case_id: str,
    milestone_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Delete a milestone from a CSR case."""
    ms = MilestoneManager.get_milestone(milestone_id)
    if ms is None or ms.get("case_id") != case_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "Milestone not found", "milestone_id": milestone_id},
        )

    success = MilestoneManager.delete_milestone(milestone_id)
    return {
        "status": "success" if success else "failed",
        "milestone_id": milestone_id,
    }


@router.get("/{case_id}/timeline", summary="Get CSR project timeline monitoring report")
async def get_case_timeline_endpoint(
    case_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """
    Get CSR project timeline monitoring dashboard data including:
    - Overall completion percentage
    - Total budget allocation vs actual spend
    - Delay alerts and schedule health
    - Gantt timeline phase breakdown
    """
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    summary = MilestoneManager.get_timeline_summary(case_id)
    milestones = MilestoneManager.get_case_milestones(case_id)

    # Build Gantt timeline phases
    phases = []
    for ms in milestones:
        phases.append({
            "milestone_id": ms["milestone_id"],
            "title": ms["title"],
            "status": ms["status"],
            "target_date": ms["target_date"],
            "completion_date": ms["completion_date"],
            "progress_percentage": ms["progress_percentage"],
            "allocated_budget": ms["allocated_budget"],
            "spent_amount": ms["spent_amount"],
            "is_delayed": ms["is_delayed"],
            "delay_days": ms["delay_days"],
        })

    return {
        "case_id": case_id,
        "case_title": case.get("title"),
        "monitoring_summary": summary,
        "timeline_phases": phases,
    }


def register_milestone_routes(app: FastAPI) -> None:
    """Register milestone routes on FastAPI app."""
    app.include_router(router)
    logger.info("✓ CSR Milestone & Timeline routes registered: /cases/{id}/milestones, /cases/{id}/timeline")
