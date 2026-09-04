"""
Comprehensive Tests for 3 CSR User Roles (CSR Head, Project Manager, Approver/Auditor) RBAC System.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from routes.case_routes import _CASE_REGISTRY
from routes.routes import _DOC_REGISTRY

client = TestClient(app)

HEAD_HEADERS = {"Authorization": "Bearer csr-head-token"}
PM_HEADERS = {"Authorization": "Bearer pm-token"}
AUDITOR_HEADERS = {"Authorization": "Bearer auditor-token"}


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear registries before each test."""
    _CASE_REGISTRY.clear()
    _DOC_REGISTRY.clear()
    yield
    _CASE_REGISTRY.clear()
    _DOC_REGISTRY.clear()


# ===========================================================================
# 1. CSR HEAD (ADMIN) TESTS
# ===========================================================================

def test_csr_head_create_and_assign_project():
    """Test CSR Head creating a project and assigning PM and Auditor."""
    case_id = "CASE-HEAD-100"
    res = client.post(
        "/rbac/head/projects",
        headers=HEAD_HEADERS,
        json={
            "case_id": case_id,
            "title": "Digital Literacy & Clean Energy Initiative",
            "total_budget": 5000000.0,
            "assigned_pm_id": "pm_exec_101",
            "assigned_auditor_id": "auditor_rev_201",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["assigned_pm_id"] == "pm_exec_101"
    assert data["assigned_auditor_id"] == "auditor_rev_201"


def test_csr_head_view_all_projects():
    """Test CSR Head viewing all projects across the entire programme."""
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": "CASE-1", "title": "Proj 1"})
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": "CASE-2", "title": "Proj 2"})

    res = client.get("/rbac/head/projects", headers=HEAD_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["total_projects"] == 2
    assert data["user_role"] == "csr_head"


# ===========================================================================
# 2. PROJECT MANAGER (EXECUTION) TESTS
# ===========================================================================

def test_pm_assigned_project_access_and_isolation():
    """Test PM viewing ONLY projects assigned to them."""
    # Case assigned to PM
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": "CASE-PM-PASS", "title": "PM Project", "assigned_pm_id": "pm_exec_101"})
    # Case assigned to different PM
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": "CASE-PM-OTHER", "title": "Other PM Project", "assigned_pm_id": "pm_other_999"})

    res = client.get("/rbac/pm/projects", headers=PM_HEADERS)
    assert res.status_code == 200
    projects = res.json()["projects"]
    assert len(projects) >= 1
    assert any(p["case_id"] == "CASE-PM-PASS" for p in projects)


def test_pm_upload_document_and_update_milestones():
    """Test PM uploading execution documents and updating milestone progress."""
    case_id = "CASE-PM-EXEC"
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": case_id, "title": "Exec Project", "assigned_pm_id": "pm_exec_101"})

    # 1. PM uploads progress report
    res_doc = client.post(
        f"/rbac/pm/projects/{case_id}/documents",
        headers=PM_HEADERS,
        json={
            "document_id": "DOC-PROGRESS-01",
            "filename": "q3_progress_report.pdf",
            "document_type": "progress_report",
            "raw_text": "Progress report Q3 completed 75 percent milestone",
        },
    )
    assert res_doc.status_code == 200

    # 2. PM updates milestone
    res_ms = client.post(
        f"/rbac/pm/projects/{case_id}/milestones",
        headers=PM_HEADERS,
        json={
            "title": "Phase 1 Execution",
            "target_date": "2026-11-30",
            "allocated_budget": 1000000.0,
            "progress_percentage": 75.0,
            "spent_amount": 700000.0,
        },
    )
    assert res_ms.status_code == 200
    assert res_ms.json()["milestone"]["progress_percentage"] == 75.0


def test_pm_submit_and_transition_stage():
    """Test PM submitting project for review and updating execution stage."""
    case_id = "CASE-PM-SUBMIT"
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": case_id, "title": "Submit Case", "assigned_pm_id": "pm_exec_101"})

    # PM submits proposal (Draft -> Submitted)
    res_sub = client.post(f"/rbac/pm/projects/{case_id}/submit", headers=PM_HEADERS)
    assert res_sub.status_code == 200
    assert res_sub.json()["current_stage"] == "SUBMITTED"


def test_pm_restricted_actions_blocked():
    """Test HTTP 403 Forbidden enforcement on actions blocked for PM role."""
    # 1. PM cannot create project via CSR Head endpoint
    res_create = client.post(
        "/rbac/head/projects",
        headers=PM_HEADERS,
        json={"case_id": "BLOCKED-PM-CREATE", "title": "Blocked PM Project"},
    )
    assert res_create.status_code == 403

    # 2. PM cannot approve project
    case_id = "CASE-PM-BLOCK-APP"
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": case_id, "title": "Block App Case", "assigned_pm_id": "pm_exec_101"})
    res_app = client.post(
        f"/rbac/auditor/projects/{case_id}/decision",
        headers=PM_HEADERS,
        json={"action": "APPROVE", "comments": "PM trying self approve"},
    )
    assert res_app.status_code == 403


# ===========================================================================
# 3. APPROVER / AUDITOR TESTS
# ===========================================================================

def test_auditor_assigned_access_and_audit_pack():
    """Test Auditor viewing assigned projects and reviewing full audit pack."""
    case_id = "CASE-AUD-PACK"
    client.post(
        "/rbac/head/projects",
        headers=HEAD_HEADERS,
        json={
            "case_id": case_id,
            "title": "Solar Electrification Audit Case",
            "total_budget": 2000000.0,
            "assigned_pm_id": "pm_exec_101",
            "assigned_auditor_id": "auditor_rev_201",
        },
    )

    # Fetch audit pack
    res_pack = client.get(f"/rbac/auditor/projects/{case_id}/audit-pack", headers=AUDITOR_HEADERS)
    assert res_pack.status_code == 200
    pack = res_pack.json()
    assert pack["case_id"] == case_id
    assert "statutory_compliance_report" in pack
    assert "milestones_summary" in pack


def test_auditor_decision_and_complete():
    """Test Auditor submitting approval decision and marking project completed."""
    case_id = "CASE-AUD-DEC"
    client.post(
        "/rbac/head/projects",
        headers=HEAD_HEADERS,
        json={"case_id": case_id, "title": "Auditor Decision Case", "assigned_auditor_id": "auditor_rev_201"},
    )
    
    # PM submits
    client.post(f"/rbac/pm/projects/{case_id}/submit", headers=PM_HEADERS)

    # Auditor approves
    res_dec = client.post(
        f"/rbac/auditor/projects/{case_id}/decision",
        headers=AUDITOR_HEADERS,
        json={"action": "APPROVE", "comments": "Compliance verified and approved."},
    )
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] == "success"

    # Auditor marks completed
    res_comp = client.post(f"/rbac/auditor/projects/{case_id}/complete", headers=AUDITOR_HEADERS)
    assert res_comp.status_code == 200
    assert res_comp.json()["status_label"] == "VERIFIED_COMPLETED"


def test_auditor_separation_of_duties_enforcement():
    """Test Separation of Duties: Creator cannot approve their own project."""
    case_id = "CASE-SELF-APP"
    # CSR Head creates case with creator_id = head_csr_001
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": case_id, "title": "Self App Case"})

    # PM submits
    client.post(f"/rbac/pm/projects/{case_id}/submit", headers=PM_HEADERS)

    # CSR Head attempts to approve project they created -> HTTP 403 Separation of Duties Violation!
    res_self = client.post(
        f"/rbac/auditor/projects/{case_id}/decision",
        headers=HEAD_HEADERS,  # Same user who created the project!
        json={"action": "APPROVE", "comments": "Self approval attempt"},
    )
    assert res_self.status_code == 403
    assert "Separation of Duties Violation" in res_self.json()["detail"]["message"]


def test_csr_head_auto_discovery_and_budget_spent_calculation():
    """Test CSR Head dynamic aggregation of uploaded document fields for budget and spent totals."""
    _DOC_REGISTRY["DOC-SURYODAYA-01"] = {
        "document_id": "DOC-SURYODAYA-01",
        "filename": "01_Suryodaya_Proposal.pdf",
        "document_type": "Project Proposal",
        "extracted_fields": [
            {"field": "project_title", "value": "Suryodaya Scholarship & Digital Learning Initiative"},
            {"field": "total_budget", "value": "₹ 65,00,000"},
            {"field": "spent_amount", "value": "₹ 15,00,000"},
        ],
        "verification_status": "verified",
        "owner_id": "pm_exec_101",
    }

    res = client.get("/rbac/head/projects", headers=HEAD_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["total_projects"] >= 1
    assert data["total_program_budget"] == 6500000.0
    assert data["total_program_spent"] == 1500000.0
    matching = [p for p in data["projects"] if p["title"] == "Suryodaya Scholarship & Digital Learning Initiative"]
    assert len(matching) == 1
    assert matching[0]["total_budget"] == 6500000.0
    assert matching[0]["total_spent"] == 1500000.0


def test_csr_head_user_management_and_lifecycle_controls():
    """Test CSR Head managing users, updating roles, editing project details, and performing admin override."""
    # 1. Get user list
    res_u = client.get("/rbac/head/users", headers=HEAD_HEADERS)
    assert res_u.status_code == 200
    assert res_u.json()["total_users"] >= 5

    # 2. Add user
    res_add = client.post(
        "/rbac/head/users",
        headers=HEAD_HEADERS,
        json={"user_id": "pm_exec_103", "name": "Anjali Sharma", "email": "anjali@csrflow.com", "role": "project_manager"},
    )
    assert res_add.status_code == 200
    assert res_add.json()["user"]["role"] == "project_manager"

    # 3. Update user role
    res_role = client.patch(
        "/rbac/head/users/pm_exec_103/role",
        headers=HEAD_HEADERS,
        json={"role": "auditor"},
    )
    assert res_role.status_code == 200
    assert res_role.json()["user"]["role"] == "auditor"

    # 4. Edit project details & baseline budget
    case_id = "CASE-HEAD-EDIT"
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": case_id, "title": "Draft Title"})
    res_edit = client.patch(
        f"/rbac/head/projects/{case_id}/details",
        headers=HEAD_HEADERS,
        json={"title": "Updated Title", "total_budget": 8000000.0},
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["project"]["title"] == "Updated Title"

    # 5. Admin override
    res_override = client.post(
        f"/rbac/head/projects/{case_id}/override",
        headers=HEAD_HEADERS,
        json={"target_stage": "MONITORING", "comments": "Emergency override"},
    )
    assert res_override.status_code == 200
    assert res_override.json()["new_stage"] == "MONITORING"

    # 6. Close project
    res_close = client.patch(f"/rbac/head/projects/{case_id}/close", headers=HEAD_HEADERS)
    assert res_close.status_code == 200
    assert res_close.json()["new_stage"] == "CLOSED"


def test_auditor_document_verification():
    """Test Auditor document-level approval/rejection/hold verification."""
    case_id = "CASE-DOC-AUDIT"
    client.post("/rbac/head/projects", headers=HEAD_HEADERS, json={"case_id": case_id, "title": "Doc Audit Project"})

    # PM uploads document
    doc_id = "DOC-AUDIT-99"
    client.post(
        f"/rbac/pm/projects/{case_id}/documents",
        headers=PM_HEADERS,
        json={"document_id": doc_id, "filename": "q3_invoice.pdf", "document_type": "invoice", "raw_text": "Invoice total $5000"},
    )

    # Auditor approves document
    res_verify = client.post(
        f"/rbac/auditor/projects/{case_id}/documents/{doc_id}/verify",
        headers=AUDITOR_HEADERS,
        json={"status": "verified", "comments": "Invoice verified against bank transaction"},
    )
    assert res_verify.status_code == 200
    assert res_verify.json()["status"] == "success"
    assert res_verify.json()["verification_status"] == "verified"

    # Check audit pack contains updated verification status
    res_pack = client.get(f"/rbac/auditor/projects/{case_id}/audit-pack", headers=AUDITOR_HEADERS)
    assert res_pack.status_code == 200
    docs = res_pack.json()["documents"]
    matching = [d for d in docs if d["document_id"] == doc_id]
    assert len(matching) == 1
    assert matching[0]["verification_status"] == "verified"



