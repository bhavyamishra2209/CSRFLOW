"""
Tests for CSR Approval Workflow Engine and API Routes.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from workflow.approval_engine import (
    WorkflowEngine,
    ApprovalStage,
    ApprovalAction,
    TRANSITION_MATRIX,
)
from routes.case_routes import _CASE_REGISTRY
from routes.routes import _DOC_REGISTRY

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-token"}


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear registries before each test."""
    _CASE_REGISTRY.clear()
    _DOC_REGISTRY.clear()
    yield
    _CASE_REGISTRY.clear()
    _DOC_REGISTRY.clear()


def test_allowed_actions_by_stage():
    """Test getting allowed actions for every approval stage."""
    draft_actions = WorkflowEngine.get_allowed_actions(ApprovalStage.DRAFT.value)
    assert ApprovalAction.SUBMIT.value in draft_actions

    review_actions = WorkflowEngine.get_allowed_actions(ApprovalStage.CSR_COMMITTEE_REVIEW.value)
    assert ApprovalAction.APPROVE.value in review_actions
    assert ApprovalAction.REJECT.value in review_actions
    assert ApprovalAction.REQUEST_REVISION.value in review_actions

    approved_actions = WorkflowEngine.get_allowed_actions(ApprovalStage.APPROVED.value)
    assert len(approved_actions) == 0


def test_transition_matrix_integrity():
    """Test transition matrix validity."""
    assert WorkflowEngine.can_transition(ApprovalStage.DRAFT.value, ApprovalAction.SUBMIT.value)
    assert WorkflowEngine.can_transition(ApprovalStage.SUBMITTED.value, ApprovalAction.APPROVE.value)
    assert not WorkflowEngine.can_transition(ApprovalStage.DRAFT.value, ApprovalAction.APPROVE.value)
    assert not WorkflowEngine.can_transition(ApprovalStage.APPROVED.value, ApprovalAction.SUBMIT.value)


def test_execute_transition_and_audit_trail():
    """Test executing stage transitions and audit trail creation."""
    case_data = {
        "case_id": "TEST-CASE-001",
        "title": "Solar Electrification CSR",
        "current_stage": ApprovalStage.DRAFT.value,
        "workflow_history": [],
    }

    # Transition 1: DRAFT -> SUBMITTED
    updated_case, log1 = WorkflowEngine.execute_transition(
        case_data=case_data,
        action=ApprovalAction.SUBMIT.value,
        actor_id="user_123",
        actor_role="PROJECT_LEAD",
        comments="Submitting for screening",
    )
    assert updated_case["current_stage"] == ApprovalStage.SUBMITTED.value
    assert len(updated_case["workflow_history"]) == 1
    assert log1["previous_stage"] == ApprovalStage.DRAFT.value
    assert log1["new_stage"] == ApprovalStage.SUBMITTED.value

    # Transition 2: SUBMITTED -> DOCUMENT_VERIFICATION
    updated_case, log2 = WorkflowEngine.execute_transition(
        case_data=updated_case,
        action=ApprovalAction.APPROVE.value,
        actor_id="verifier_01",
        actor_role="DOCUMENT_VERIFIER",
        comments="Documents verified successfully",
    )
    assert updated_case["current_stage"] == ApprovalStage.DOCUMENT_VERIFICATION.value
    assert len(updated_case["workflow_history"]) == 2
    assert log2["previous_stage"] == ApprovalStage.SUBMITTED.value
    assert log2["new_stage"] == ApprovalStage.DOCUMENT_VERIFICATION.value


def test_full_e2e_approval_lifecycle_api():
    """Test full E2E approval lifecycle via FastAPI endpoints."""
    case_id = "CASE-E2E-100"

    # Step 1: Create case
    res1 = client.post(
        "/cases",
        headers=AUTH_HEADERS,
        json={"case_id": case_id, "title": "E2E CSR Project"},
    )
    assert res1.status_code == 200

    # Step 2: Submit case (DRAFT -> SUBMITTED)
    res2 = client.post(
        f"/cases/{case_id}/workflow/submit",
        headers=AUTH_HEADERS,
        json={"comments": "Submitting project for governance review"},
    )
    assert res2.status_code == 200
    assert res2.json()["current_stage"] == "SUBMITTED"

    # Step 3: Verify documents (SUBMITTED -> DOCUMENT_VERIFICATION)
    res3 = client.post(
        f"/cases/{case_id}/workflow/action",
        headers=AUTH_HEADERS,
        json={"action": "APPROVE", "reviewer_role": "DOCUMENT_VERIFIER", "comments": "Docs complete"},
    )
    assert res3.status_code == 200
    assert res3.json()["current_stage"] == "DOCUMENT_VERIFICATION"

    # Step 4: CSR Committee Approval (DOCUMENT_VERIFICATION -> CSR_COMMITTEE_REVIEW -> FINANCIAL_AUDIT)
    res4 = client.post(
        f"/cases/{case_id}/workflow/action",
        headers=AUTH_HEADERS,
        json={"action": "APPROVE", "reviewer_role": "CSR_COMMITTEE_MEMBER", "comments": "Committee approved"},
    )
    assert res4.status_code == 200
    assert res4.json()["current_stage"] == "CSR_COMMITTEE_REVIEW"

    res5 = client.post(
        f"/cases/{case_id}/workflow/action",
        headers=AUTH_HEADERS,
        json={"action": "APPROVE", "reviewer_role": "CSR_COMMITTEE_MEMBER", "comments": "Moving to Finance"},
    )
    assert res5.status_code == 200
    assert res5.json()["current_stage"] == "FINANCIAL_AUDIT"

    # Step 5: Final Finance Approval (FINANCIAL_AUDIT -> APPROVED)
    res6 = client.post(
        f"/cases/{case_id}/workflow/action",
        headers=AUTH_HEADERS,
        json={"action": "APPROVE", "reviewer_role": "FINANCIAL_AUDITOR", "comments": "Funds authorized"},
    )
    assert res6.status_code == 200
    assert res6.json()["current_stage"] == "APPROVED"

    # Step 6: Verify history log
    res_hist = client.get(f"/cases/{case_id}/workflow/history", headers=AUTH_HEADERS)
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert hist["total_steps"] == 5


def test_revision_and_resubmit_loop_api():
    """Test revision request and resubmission loop."""
    case_id = "CASE-REV-200"

    client.post("/cases", headers=AUTH_HEADERS, json={"case_id": case_id, "title": "Revision Project"})
    client.post(f"/cases/{case_id}/workflow/submit", headers=AUTH_HEADERS)
    client.post(
        f"/cases/{case_id}/workflow/action",
        headers=AUTH_HEADERS,
        json={"action": "APPROVE"},
    )

    # Request revision at DOCUMENT_VERIFICATION stage
    res_rev = client.post(
        f"/cases/{case_id}/workflow/action",
        headers=AUTH_HEADERS,
        json={"action": "REQUEST_REVISION", "comments": "Please update total budget format"},
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["current_stage"] == "REVISION_REQUESTED"

    # Resubmit case
    res_resubmit = client.post(
        f"/cases/{case_id}/workflow/submit",
        headers=AUTH_HEADERS,
        json={"comments": "Updated budget format as requested"},
    )
    assert res_resubmit.status_code == 200
    assert res_resubmit.json()["current_stage"] == "SUBMITTED"


def test_pending_workflows_query_api():
    """Test listing pending workflows."""
    c1 = "CASE-PND-1"
    c2 = "CASE-PND-2"

    client.post("/cases", headers=AUTH_HEADERS, json={"case_id": c1, "title": "Pending 1"})
    client.post("/cases", headers=AUTH_HEADERS, json={"case_id": c2, "title": "Pending 2"})
    client.post(f"/cases/{c1}/workflow/submit", headers=AUTH_HEADERS)

    res = client.get("/workflows/pending", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["total_pending"] == 2
