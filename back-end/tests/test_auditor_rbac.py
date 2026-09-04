"""
Tests for Auditor / Approver Role-Based Access Control (RBAC) System.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from routes.case_routes import _CASE_REGISTRY
from routes.routes import _DOC_REGISTRY

client = TestClient(app)

AUDITOR_HEADERS = {"Authorization": "Bearer auditor-token"}
ADMIN_HEADERS = {"Authorization": "Bearer dev-token"}


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear registries before each test."""
    _CASE_REGISTRY.clear()
    _DOC_REGISTRY.clear()
    yield
    _CASE_REGISTRY.clear()
    _DOC_REGISTRY.clear()


def test_auditor_authentication_and_token():
    """Test auditor-token login returning auditor role."""
    res = client.get("/auditor/cases", headers=AUDITOR_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["auditor_user_id"] == "auditor_rev_201"
    assert data["auditor_role"] == "auditor"


def test_auditor_assigned_case_listing():
    """Test Auditor listing only assigned projects."""
    # Create two cases as Admin
    client.post("/cases", headers=ADMIN_HEADERS, json={"case_id": "CASE-AUD-1", "title": "Assigned Case"})
    client.post("/cases", headers=ADMIN_HEADERS, json={"case_id": "CASE-AUD-2", "title": "Unassigned Case"})

    # Assign auditor to CASE-AUD-1
    client.post(
        "/cases/CASE-AUD-1/assign-auditor",
        headers=ADMIN_HEADERS,
        json={"auditor_id": "auditor_rev_201"},
    )

    # Fetch assigned cases for auditor
    res = client.get("/auditor/cases", headers=AUDITOR_HEADERS)
    assert res.status_code == 200
    cases = res.json()["cases"]
    assert len(cases) >= 1
    matched = [c for c in cases if c["case_id"] == "CASE-AUD-1"]
    assert len(matched) == 1


def test_auditor_review_dashboard_aggregation():
    """Test Auditor review dashboard returning docs, milestones, compliance, and allowed actions."""
    case_id = "CASE-DASHBOARD-10"
    client.post("/cases", headers=ADMIN_HEADERS, json={"case_id": case_id, "title": "Dashboard Audit Case"})

    res = client.get(f"/auditor/cases/{case_id}/review-dashboard", headers=AUDITOR_HEADERS)
    assert res.status_code == 200
    dash = res.json()

    assert dash["case_id"] == case_id
    assert dash["project_title"] == "Dashboard Audit Case"
    assert "compliance_and_risk" in dash
    assert "milestone_summary" in dash
    assert "audit_trail_history" in dash


def test_auditor_decision_execution():
    """Test Auditor submitting formal approval decision."""
    case_id = "CASE-DECISION-20"
    client.post("/cases", headers=ADMIN_HEADERS, json={"case_id": case_id, "title": "Decision Case"})

    # Submit case first
    client.post(f"/cases/{case_id}/workflow/submit", headers=ADMIN_HEADERS, json={"comments": "Submitting"})

    # Auditor approves case
    res = client.post(
        f"/auditor/cases/{case_id}/decision",
        headers=AUDITOR_HEADERS,
        json={"action": "APPROVE", "comments": "Auditor verifies compliance and approves project."},
    )

    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "success"
    assert res_data["auditor_id"] == "auditor_rev_201"
    assert res_data["new_stage"] in ("DOCUMENT_VERIFICATION", "CSR_COMMITTEE_REVIEW", "FINANCIAL_AUDIT")


def test_auditor_restricted_actions_blocked():
    """Test strict HTTP 403 Forbidden enforcement on restricted actions for Auditor role."""
    # 1. Auditor cannot create new projects
    res_create = client.post(
        "/cases",
        headers=AUDITOR_HEADERS,
        json={"case_id": "BLOCKED-CASE", "title": "Auditor Created Project"},
    )
    assert res_create.status_code == 403
    assert "Auditor role cannot create new projects" in res_create.json()["detail"]["message"]

    # 2. Auditor cannot assign PMs
    client.post("/cases", headers=ADMIN_HEADERS, json={"case_id": "CASE-RESTRICTED-30", "title": "Restricted Case"})
    res_pm = client.patch(
        "/cases/CASE-RESTRICTED-30/assign-pm",
        headers=AUDITOR_HEADERS,
        json={"pm_id": "pm_user_789"},
    )
    assert res_pm.status_code == 403
    assert "Auditor role cannot assign Project Managers" in res_pm.json()["detail"]["message"]

    # 3. Auditor cannot self-assign auditors
    res_assign = client.post(
        "/cases/CASE-RESTRICTED-30/assign-auditor",
        headers=AUDITOR_HEADERS,
        json={"auditor_id": "auditor_user_456"},
    )
    assert res_assign.status_code == 403
    assert "Auditors cannot self-assign" in res_assign.json()["detail"]["message"]
