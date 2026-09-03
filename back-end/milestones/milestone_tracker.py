"""
CSR Milestone & Timeline Tracking Manager.

Manages milestone creation, progress tracking, budget utilization,
delay detection, and case timeline aggregation for CSR project monitoring.
"""

import uuid
import datetime
import logging
from enum import Enum
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MilestoneStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"


# In-memory Registry for Milestones
# Shape: { milestone_id: { ... milestone_item_dict ... } }
_MILESTONE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _check_is_delayed(target_date_str: Optional[str], status: str) -> tuple[bool, int]:
    """Calculate if milestone is delayed beyond target_date."""
    if status in (MilestoneStatus.COMPLETED.value, MilestoneStatus.CANCELLED.value) or not target_date_str:
        return False, 0
    try:
        target_dt = datetime.date.fromisoformat(target_date_str[:10])
        today = datetime.date.today()
        if today > target_dt:
            delay = (today - target_dt).days
            return True, delay
    except Exception:
        pass
    return False, 0


class MilestoneManager:
    """Manager for CSR Project Milestones and Timeline Calculations."""

    @staticmethod
    def create_milestone(
        case_id: str,
        title: str,
        target_date: str,
        description: str = "",
        allocated_budget: float = 0.0,
        target_beneficiaries: int = 0,
        milestone_id: Optional[str] = None,
        evidence_document_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new CSR project milestone."""
        mid = milestone_id or f"MS-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        is_delayed, delay_days = _check_is_delayed(target_date, MilestoneStatus.PLANNED.value)
        status = MilestoneStatus.DELAYED.value if is_delayed else MilestoneStatus.PLANNED.value

        milestone = {
            "milestone_id": mid,
            "case_id": case_id,
            "title": title,
            "description": description,
            "status": status,
            "target_date": target_date,
            "completion_date": None,
            "allocated_budget": float(allocated_budget),
            "spent_amount": 0.0,
            "progress_percentage": 0.0,
            "target_beneficiaries": int(target_beneficiaries),
            "achieved_beneficiaries": 0,
            "evidence_document_ids": evidence_document_ids or [],
            "is_delayed": is_delayed,
            "delay_days": delay_days,
            "created_at": now,
            "updated_at": now,
        }

        _MILESTONE_REGISTRY[mid] = milestone
        logger.info(f"Created milestone '{mid}' for case '{case_id}'")
        return milestone

    @staticmethod
    def get_milestone(milestone_id: str) -> Optional[Dict[str, Any]]:
        """Fetch single milestone by ID."""
        ms = _MILESTONE_REGISTRY.get(milestone_id)
        if ms:
            # Refresh delay status
            is_delayed, delay_days = _check_is_delayed(ms.get("target_date"), ms.get("status"))
            ms["is_delayed"] = is_delayed
            ms["delay_days"] = delay_days
            if is_delayed and ms["status"] not in (MilestoneStatus.COMPLETED.value, MilestoneStatus.CANCELLED.value):
                ms["status"] = MilestoneStatus.DELAYED.value
        return ms

    @staticmethod
    def get_case_milestones(case_id: str) -> List[Dict[str, Any]]:
        """Get all milestones belonging to a case."""
        result = []
        for ms in _MILESTONE_REGISTRY.values():
            if ms.get("case_id") == case_id:
                m_copy = ms.copy()
                is_delayed, delay_days = _check_is_delayed(m_copy.get("target_date"), m_copy.get("status"))
                m_copy["is_delayed"] = is_delayed
                m_copy["delay_days"] = delay_days
                if is_delayed and m_copy["status"] not in (MilestoneStatus.COMPLETED.value, MilestoneStatus.CANCELLED.value):
                    m_copy["status"] = MilestoneStatus.DELAYED.value
                result.append(m_copy)
        
        # Sort by target_date
        result.sort(key=lambda x: x.get("target_date") or "")
        return result

    @staticmethod
    def update_milestone(milestone_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing milestone."""
        ms = _MILESTONE_REGISTRY.get(milestone_id)
        if not ms:
            return None

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Update allowed fields
        for key in (
            "title", "description", "status", "target_date", "completion_date",
            "allocated_budget", "spent_amount", "progress_percentage",
            "target_beneficiaries", "achieved_beneficiaries", "evidence_document_ids"
        ):
            if key in updates and updates[key] is not None:
                ms[key] = updates[key]

        # Auto-update status based on progress_percentage if not explicitly set
        prog = ms.get("progress_percentage", 0.0)
        if prog >= 100.0 and ms.get("status") != MilestoneStatus.COMPLETED.value:
            ms["status"] = MilestoneStatus.COMPLETED.value
            if not ms.get("completion_date"):
                ms["completion_date"] = datetime.date.today().isoformat()
        elif 0.0 < prog < 100.0 and ms.get("status") == MilestoneStatus.PLANNED.value:
            ms["status"] = MilestoneStatus.IN_PROGRESS.value

        # Refresh delay status
        is_delayed, delay_days = _check_is_delayed(ms.get("target_date"), ms.get("status"))
        ms["is_delayed"] = is_delayed
        ms["delay_days"] = delay_days
        if is_delayed and ms["status"] not in (MilestoneStatus.COMPLETED.value, MilestoneStatus.CANCELLED.value):
            ms["status"] = MilestoneStatus.DELAYED.value

        ms["updated_at"] = now
        _MILESTONE_REGISTRY[milestone_id] = ms
        logger.info(f"Updated milestone '{milestone_id}'")
        return ms

    @staticmethod
    def delete_milestone(milestone_id: str) -> bool:
        """Delete milestone from registry."""
        if milestone_id in _MILESTONE_REGISTRY:
            del _MILESTONE_REGISTRY[milestone_id]
            logger.info(f"Deleted milestone '{milestone_id}'")
            return True
        return False

    @staticmethod
    def get_timeline_summary(case_id: str) -> Dict[str, Any]:
        """Compute aggregate project monitoring & timeline health metrics for a case."""
        milestones = MilestoneManager.get_case_milestones(case_id)
        
        total_count = len(milestones)
        if total_count == 0:
            return {
                "case_id": case_id,
                "total_milestones": 0,
                "completed_milestones": 0,
                "in_progress_milestones": 0,
                "delayed_milestones": 0,
                "overall_progress_percentage": 0.0,
                "total_allocated_budget": 0.0,
                "total_spent_amount": 0.0,
                "budget_utilization_percentage": 0.0,
                "target_beneficiaries": 0,
                "achieved_beneficiaries": 0,
                "timeline_health": "NO_MILESTONES",
                "is_behind_schedule": False,
                "next_milestone": None,
            }

        completed = sum(1 for m in milestones if m.get("status") == MilestoneStatus.COMPLETED.value)
        in_progress = sum(1 for m in milestones if m.get("status") == MilestoneStatus.IN_PROGRESS.value)
        delayed = sum(1 for m in milestones if m.get("is_delayed"))

        total_progress = sum(m.get("progress_percentage", 0.0) for m in milestones)
        overall_progress = round(total_progress / total_count, 2)

        allocated_sum = sum(m.get("allocated_budget", 0.0) for m in milestones)
        spent_sum = sum(m.get("spent_amount", 0.0) for m in milestones)
        utilization = round((spent_sum / allocated_sum * 100.0), 2) if allocated_sum > 0 else 0.0

        target_ben = sum(m.get("target_beneficiaries", 0) for m in milestones)
        achieved_ben = sum(m.get("achieved_beneficiaries", 0) for m in milestones)

        # Timeline Health Status
        if delayed > 0:
            health = "CRITICAL_DELAY" if delayed > 1 else "MINOR_DELAY"
        elif overall_progress >= 100.0:
            health = "COMPLETED"
        elif in_progress > 0 or completed > 0:
            health = "ON_TRACK"
        else:
            health = "PLANNED"

        # Find next upcoming milestone
        upcoming = [m for m in milestones if m.get("status") in (MilestoneStatus.PLANNED.value, MilestoneStatus.IN_PROGRESS.value, MilestoneStatus.DELAYED.value)]
        next_ms = upcoming[0] if upcoming else None

        return {
            "case_id": case_id,
            "total_milestones": total_count,
            "completed_milestones": completed,
            "in_progress_milestones": in_progress,
            "delayed_milestones": delayed,
            "overall_progress_percentage": overall_progress,
            "total_allocated_budget": allocated_sum,
            "total_spent_amount": spent_sum,
            "budget_utilization_percentage": utilization,
            "target_beneficiaries": target_ben,
            "achieved_beneficiaries": achieved_ben,
            "timeline_health": health,
            "is_behind_schedule": delayed > 0,
            "next_milestone": next_ms,
        }
