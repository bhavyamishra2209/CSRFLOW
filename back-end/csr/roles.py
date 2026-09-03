"""
CSR role definitions and permission helpers.

Three roles only:
  csr_head        — overall CSR program manager
  project_manager — day-to-day project execution
  approver        — independent reviewer / auditor
"""

from enum import Enum
from typing import Set


class UserRole(str, Enum):
    CSR_HEAD        = "csr_head"
    PROJECT_MANAGER = "project_manager"
    APPROVER        = "approver"

    def label(self) -> str:
        return {
            "csr_head":        "CSR Head",
            "project_manager": "Project Manager",
            "approver":        "Approver / Auditor",
        }[self.value]

    def dashboard_path(self) -> str:
        return {
            "csr_head":        "/csr/head",
            "project_manager": "/csr/pm",
            "approver":        "/csr/approver",
        }[self.value]

    def description(self) -> str:
        return {
            "csr_head": (
                "Creates and manages CSR projects, assigns Project Managers, "
                "tracks budgets and compliance, views all reports."
            ),
            "project_manager": (
                "Executes assigned projects, uploads documents, tracks milestones "
                "and expenses, uses AI document Q&A."
            ),
            "approver": (
                "Reviews proposals, approves or rejects project stages, verifies "
                "the audit trail. Cannot approve own work."
            ),
        }[self.value]


# ---------------------------------------------------------------------------
# Permission sets
# ---------------------------------------------------------------------------

# Who can read every project (not just their assigned one)
CAN_READ_ALL_PROJECTS: Set[str] = {"csr_head"}

# Who can create a new project
CAN_CREATE_PROJECT: Set[str] = {"csr_head"}

# Who can assign a PM or approver to a project
CAN_ASSIGN_MEMBERS: Set[str] = {"csr_head"}

# Who can upload documents / update milestones on a project
CAN_UPDATE_PROJECT_CONTENT: Set[str] = {"csr_head", "project_manager"}

# Who can submit a project for approval (move draft → submitted)
CAN_SUBMIT_PROJECT: Set[str] = {"csr_head", "project_manager"}

# Who can approve or reject a stage transition
CAN_APPROVE_STAGE: Set[str] = {"approver"}

# Who can forcibly move any stage (admin override)
CAN_OVERRIDE_STAGE: Set[str] = {"csr_head"}

# Who can view the full audit trail
CAN_VIEW_AUDIT: Set[str] = {"csr_head", "approver"}

# Who can manage user accounts / assign roles
CAN_MANAGE_USERS: Set[str] = {"csr_head"}

ALL_ROLES: Set[str] = {r.value for r in UserRole}
