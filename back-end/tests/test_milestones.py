"""
Tests for CSR Milestone & Timeline Tracking Manager and API Routes.
"""

import pytest
import datetime
from fastapi.testclient import TestClient

from main import app
from milestones.milestone_tracker import MilestoneManager, MilestoneStatus, _MILESTONE_REGISTRY
from routes.case_routes import _CASE_REGISTRY

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-token"}


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear registries before each test."""
    _CASE_REGISTRY.clear()
    _MILESTONE_REGISTRY.clear()
    yield
    _CASE_REGISTRY.clear()
    _MILESTONE_REGISTRY.clear()


def test_milestone_creation_and_retrieval():
    """Test milestone creation and fetching."""
    case_id = "CASE-MS-001"
    ms = MilestoneManager.create_milestone(
        case_id=case_id,
        title="Phase 1: Solar Panel Installation",
        target_date="2026-12-31",
        description="Install 50 solar panels",
        allocated_budget=150000.0,
        target_beneficiaries=5000,
    )

    assert ms["milestone_id"].startswith("MS-")
    assert ms["case_id"] == case_id
    assert ms["status"] == MilestoneStatus.PLANNED.value
    assert ms["allocated_budget"] == 150000.0

    fetched = MilestoneManager.get_milestone(ms["milestone_id"])
    assert fetched is not None
    assert fetched["title"] == "Phase 1: Solar Panel Installation"


def test_milestone_update_and_auto_completion():
    """Test updating milestone progress and auto-transition to COMPLETED."""
    case_id = "CASE-MS-002"
    ms = MilestoneManager.create_milestone(
        case_id=case_id,
        title="Phase 2: Water Filtration Setup",
        target_date="2026-12-31",
        allocated_budget=100000.0,
    )

    mid = ms["milestone_id"]

    # Partial progress update
    up1 = MilestoneManager.update_milestone(mid, {
        "progress_percentage": 50.0,
        "spent_amount": 40000.0,
        "status": MilestoneStatus.IN_PROGRESS.value,
    })
    assert up1["progress_percentage"] == 50.0
    assert up1["status"] == MilestoneStatus.IN_PROGRESS.value

    # Complete progress update (100%)
    up2 = MilestoneManager.update_milestone(mid, {
        "progress_percentage": 100.0,
        "spent_amount": 95000.0,
    })
    assert up2["progress_percentage"] == 100.0
    assert up2["status"] == MilestoneStatus.COMPLETED.value
    assert up2["completion_date"] is not None


def test_timeline_summary_and_budget_utilization():
    """Test aggregate milestone progress, budget utilization, and health metrics."""
    case_id = "CASE-MS-003"
    
    # Milestone 1: Completed
    ms1 = MilestoneManager.create_milestone(case_id, "MS 1", "2026-06-01", allocated_budget=50000.0, target_beneficiaries=1000)
    MilestoneManager.update_milestone(ms1["milestone_id"], {"progress_percentage": 100.0, "spent_amount": 50000.0, "achieved_beneficiaries": 1000})

    # Milestone 2: In Progress
    ms2 = MilestoneManager.create_milestone(case_id, "MS 2", "2026-12-01", allocated_budget=50000.0, target_beneficiaries=1000)
    MilestoneManager.update_milestone(ms2["milestone_id"], {"progress_percentage": 50.0, "spent_amount": 25000.0, "achieved_beneficiaries": 500})

    summary = MilestoneManager.get_timeline_summary(case_id)
    assert summary["total_milestones"] == 2
    assert summary["completed_milestones"] == 1
    assert summary["in_progress_milestones"] == 1
    assert summary["overall_progress_percentage"] == 75.0
    assert summary["total_allocated_budget"] == 100000.0
    assert summary["total_spent_amount"] == 75000.0
    assert summary["budget_utilization_percentage"] == 75.0
    assert summary["target_beneficiaries"] == 2000
    assert summary["achieved_beneficiaries"] == 1500
    assert summary["timeline_health"] == "ON_TRACK"


def test_delay_detection():
    """Test delay detection when target_date is in the past."""
    case_id = "CASE-MS-004"
    past_date = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
    
    ms = MilestoneManager.create_milestone(case_id, "Overdue Task", past_date, allocated_budget=10000.0)
    assert ms["is_delayed"] is True
    assert ms["delay_days"] == 10
    assert ms["status"] == MilestoneStatus.DELAYED.value

    summary = MilestoneManager.get_timeline_summary(case_id)
    assert summary["delayed_milestones"] == 1
    assert summary["is_behind_schedule"] is True


def test_milestone_api_endpoints():
    """Test milestone API routes end-to-end."""
    case_id = "CASE-API-500"

    # Create parent case
    client.post("/cases", headers=AUTH_HEADERS, json={"case_id": case_id, "title": "Milestone API Test Project"})

    # 1. POST /cases/{case_id}/milestones
    res_create = client.post(
        f"/cases/{case_id}/milestones",
        headers=AUTH_HEADERS,
        json={
            "title": "Phase 1: Civil Works",
            "target_date": "2026-10-15",
            "allocated_budget": 200000.0,
            "target_beneficiaries": 3000,
        },
    )
    assert res_create.status_code == 200
    ms = res_create.json()["milestone"]
    mid = ms["milestone_id"]
    assert ms["title"] == "Phase 1: Civil Works"

    # 2. GET /cases/{case_id}/milestones
    res_list = client.get(f"/cases/{case_id}/milestones", headers=AUTH_HEADERS)
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert data_list["milestone_count"] == 1

    # 3. PATCH /cases/{case_id}/milestones/{mid}
    res_patch = client.patch(
        f"/cases/{case_id}/milestones/{mid}",
        headers=AUTH_HEADERS,
        json={"progress_percentage": 75.0, "spent_amount": 150000.0, "achieved_beneficiaries": 2000},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["milestone"]["progress_percentage"] == 75.0

    # 4. GET /cases/{case_id}/timeline
    res_timeline = client.get(f"/cases/{case_id}/timeline", headers=AUTH_HEADERS)
    assert res_timeline.status_code == 200
    timeline = res_timeline.json()
    assert len(timeline["timeline_phases"]) == 1
    assert timeline["monitoring_summary"]["overall_progress_percentage"] == 75.0

    # 5. DELETE /cases/{case_id}/milestones/{mid}
    res_del = client.delete(f"/cases/{case_id}/milestones/{mid}", headers=AUTH_HEADERS)
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "success"
