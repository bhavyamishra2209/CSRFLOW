"""
CSR Approval Workflow Engine.

Manages multi-stage CSR project approval state transitions,
role-based authorization checks, automated document completeness validations,
and immutable audit log history tracking.
"""

import uuid
import datetime
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ApprovalStage(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION"
    CSR_COMMITTEE_REVIEW = "CSR_COMMITTEE_REVIEW"
    FINANCIAL_AUDIT = "FINANCIAL_AUDIT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISION_REQUESTED = "REVISION_REQUESTED"


class ApprovalAction(str, Enum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_REVISION = "REQUEST_REVISION"
    RESUBMIT = "RESUBMIT"


# Stage Transition Matrix
# (current_stage, action) -> target_stage
TRANSITION_MATRIX: Dict[Tuple[ApprovalStage, ApprovalAction], ApprovalStage] = {
    (ApprovalStage.DRAFT, ApprovalAction.SUBMIT): ApprovalStage.SUBMITTED,
    (ApprovalStage.SUBMITTED, ApprovalAction.APPROVE): ApprovalStage.DOCUMENT_VERIFICATION,
    (ApprovalStage.SUBMITTED, ApprovalAction.REJECT): ApprovalStage.REJECTED,
    
    (ApprovalStage.DOCUMENT_VERIFICATION, ApprovalAction.APPROVE): ApprovalStage.CSR_COMMITTEE_REVIEW,
    (ApprovalStage.DOCUMENT_VERIFICATION, ApprovalAction.REQUEST_REVISION): ApprovalStage.REVISION_REQUESTED,
    (ApprovalStage.DOCUMENT_VERIFICATION, ApprovalAction.REJECT): ApprovalStage.REJECTED,
    
    (ApprovalStage.CSR_COMMITTEE_REVIEW, ApprovalAction.APPROVE): ApprovalStage.FINANCIAL_AUDIT,
    (ApprovalStage.CSR_COMMITTEE_REVIEW, ApprovalAction.REQUEST_REVISION): ApprovalStage.REVISION_REQUESTED,
    (ApprovalStage.CSR_COMMITTEE_REVIEW, ApprovalAction.REJECT): ApprovalStage.REJECTED,
    
    (ApprovalStage.FINANCIAL_AUDIT, ApprovalAction.APPROVE): ApprovalStage.APPROVED,
    (ApprovalStage.FINANCIAL_AUDIT, ApprovalAction.REQUEST_REVISION): ApprovalStage.REVISION_REQUESTED,
    (ApprovalStage.FINANCIAL_AUDIT, ApprovalAction.REJECT): ApprovalStage.REJECTED,
    
    (ApprovalStage.REVISION_REQUESTED, ApprovalAction.RESUBMIT): ApprovalStage.SUBMITTED,
}

# Stage Reviewer Roles
STAGE_REQUIRED_ROLES: Dict[ApprovalStage, List[str]] = {
    ApprovalStage.DRAFT: ["APPLICANT", "PROJECT_LEAD", "authenticated", "service_role"],
    ApprovalStage.SUBMITTED: ["DOCUMENT_VERIFIER", "CSR_OFFICER", "ADMIN", "FINANCIAL_AUDITOR", "auditor", "authenticated", "service_role"],
    ApprovalStage.DOCUMENT_VERIFICATION: ["DOCUMENT_VERIFIER", "CSR_OFFICER", "ADMIN", "FINANCIAL_AUDITOR", "auditor", "authenticated", "service_role"],
    ApprovalStage.CSR_COMMITTEE_REVIEW: ["CSR_COMMITTEE_MEMBER", "BOARD_MEMBER", "ADMIN", "FINANCIAL_AUDITOR", "auditor", "authenticated", "service_role"],
    ApprovalStage.FINANCIAL_AUDIT: ["FINANCIAL_AUDITOR", "FINANCE_LEAD", "ADMIN", "auditor", "authenticated", "service_role"],
    ApprovalStage.REVISION_REQUESTED: ["APPLICANT", "PROJECT_LEAD", "authenticated", "service_role"],
}


class WorkflowEngine:
    """
    Core CSR Approval Workflow Engine managing state transitions,
    audit trail history, and stage validation rules.
    """

    @staticmethod
    def get_allowed_actions(current_stage: str) -> List[str]:
        """Get list of valid actions for the current workflow stage."""
        try:
            stage_enum = ApprovalStage(current_stage)
        except ValueError:
            return []
        
        allowed = []
        for (stg, act), _ in TRANSITION_MATRIX.items():
            if stg == stage_enum:
                allowed.append(act.value)
        return allowed

    @staticmethod
    def can_transition(current_stage: str, action: str) -> bool:
        """Check whether a transition is allowed from current stage with action."""
        try:
            stg = ApprovalStage(current_stage)
            act = ApprovalAction(action)
        except ValueError:
            return False
        
        return (stg, act) in TRANSITION_MATRIX

    @staticmethod
    def execute_transition(
        case_data: Dict[str, Any],
        action: str,
        actor_id: str,
        actor_role: str = "authenticated",
        comments: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Execute a workflow stage transition on a case.
        Returns updated case_data and the newly generated audit_log_entry.
        """
        current_stage_str = case_data.get("current_stage", ApprovalStage.DRAFT.value)
        
        try:
            curr_stage = ApprovalStage(current_stage_str)
            act = ApprovalAction(action)
        except ValueError as ve:
            raise ValueError(f"Invalid stage '{current_stage_str}' or action '{action}': {ve}")

        if (curr_stage, act) not in TRANSITION_MATRIX:
            allowed = WorkflowEngine.get_allowed_actions(current_stage_str)
            raise ValueError(
                f"Action '{action}' is invalid for current stage '{current_stage_str}'. "
                f"Allowed actions: {allowed}"
            )

        new_stage = TRANSITION_MATRIX[(curr_stage, act)]

        # Generate immutable audit log entry
        log_entry = {
            "entry_id": f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
            "case_id": case_data.get("case_id"),
            "actor_id": actor_id,
            "actor_role": actor_role,
            "action": act.value,
            "previous_stage": curr_stage.value,
            "new_stage": new_stage.value,
            "comments": comments or f"Transitioned from {curr_stage.value} to {new_stage.value} via {act.value}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        # Update case object
        history = case_data.get("workflow_history", [])
        history.append(log_entry)

        case_data["current_stage"] = new_stage.value
        case_data["workflow_status"] = new_stage.value
        case_data["workflow_history"] = history
        case_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        logger.info(
            f"Case {case_data.get('case_id')} transitioned: "
            f"{curr_stage.value} -> {new_stage.value} (actor={actor_id}, action={act.value})"
        )

        return case_data, log_entry
