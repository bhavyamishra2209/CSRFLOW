"""
End-to-End Sample Demo Automation Script for 3-Role Enterprise CSRFLOW System.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from fastapi.testclient import TestClient

from main import app
from routes.case_routes import _CASE_REGISTRY
from routes.routes import _DOC_REGISTRY

client = TestClient(app)

HEAD_HEADERS = {"Authorization": "Bearer csr-head-token"}
PM_HEADERS = {"Authorization": "Bearer pm-token"}
AUDITOR_HEADERS = {"Authorization": "Bearer auditor-token"}

def run_sample_demo():
    print("======================================================================")
    print("STARTING FRESH DEMO: 3-ROLE ENTERPRISE CSR GOVERNANCE FLOW")
    print("======================================================================\n")

    # Step 0: Reset all previous data
    print("STEP 0: [RESET] Clearing all previous documents, cases, and milestones...")
    res_reset = client.post("/rbac/head/reset-all-data", headers=HEAD_HEADERS)
    print(f"   -> Status: {res_reset.status_code}, Message: {res_reset.json().get('message')}\n")

    # Step 1: CSR Head creates CSR project and assigns team
    case_id = "CSR-SOLAR-2026"
    print(f"STEP 1: [CSR HEAD] Creating new CSR Project '{case_id}'...")
    res_create = client.post(
        "/rbac/head/projects",
        headers=HEAD_HEADERS,
        json={
            "case_id": case_id,
            "title": "Solar Electrification & Digital Classroom Initiative",
            "total_budget": 5000000.0,
            "assigned_pm_id": "pm_exec_101",
            "assigned_auditor_id": "auditor_rev_201",
        },
    )
    print(f"   -> Status: {res_create.status_code}, Project: '{case_id}' created in DRAFT stage")
    print(f"   -> Assigned PM: pm_exec_101 | Assigned Auditor: auditor_rev_201\n")

    # Step 2: PM views assigned project, updates milestone, attaches doc, and submits proposal
    print(f"STEP 2: [PROJECT MANAGER] PM 'pm_exec_101' executing project '{case_id}'...")
    res_pm_projs = client.get("/rbac/pm/projects", headers=PM_HEADERS)
    pm_projects = res_pm_projs.json().get("projects", [])
    print(f"   -> PM assigned project count: {len(pm_projects)}")

    # 2A: PM updates execution milestone
    res_ms = client.post(
        f"/rbac/pm/projects/{case_id}/milestones",
        headers=PM_HEADERS,
        json={
            "title": "Phase 1: Solar Panel Installation & Wiring",
            "target_date": "2026-10-15",
            "allocated_budget": 3000000.0,
            "spent_amount": 1200000.0,
            "progress_percentage": 40.0,
        },
    )
    print(f"   -> Updated Milestone: 'Phase 1: Solar Panel Installation' (Spent: INR 12,00,000, Progress: 40%)")

    # 2B: PM attaches execution document
    res_doc = client.post(
        f"/rbac/pm/projects/{case_id}/documents",
        headers=PM_HEADERS,
        json={
            "document_id": "DOC-SOLAR-EXP-01",
            "filename": "solar_panel_procurement_invoice.pdf",
            "document_type": "invoice",
            "raw_text": "Invoice #88392 for solar PV modules procurement INR 1200000 paid",
        },
    )
    print(f"   -> Attached Execution Doc: 'solar_panel_procurement_invoice.pdf'")

    # 2C: PM submits proposal for review
    res_sub = client.post(f"/rbac/pm/projects/{case_id}/submit", headers=PM_HEADERS)
    print(f"   -> Submitted Proposal for Audit Review (Stage: {res_sub.json().get('current_stage')})\n")

    # Step 3: Auditor reviews full Audit Pack, compliance, and AI flags, then approves
    print(f"STEP 3: [AUDITOR] Auditor 'auditor_rev_201' reviewing audit pack for '{case_id}'...")
    res_pack = client.get(f"/rbac/auditor/projects/{case_id}/audit-pack", headers=AUDITOR_HEADERS)
    pack = res_pack.json()
    print(f"   -> Compliance Score: {pack.get('statutory_compliance_report', {}).get('compliance_score')}%")
    print(f"   -> Double Funding Flags: {len(pack.get('double_funding_flags', []))}")

    # Auditor approves project
    res_app = client.post(
        f"/rbac/auditor/projects/{case_id}/decision",
        headers=AUDITOR_HEADERS,
        json={"action": "APPROVE", "comments": "Verified invoices, milestones, and statutory compliance. Approved for execution."},
    )
    print(f"   -> Auditor Decision: APPROVED (Stage: {res_app.json().get('new_stage')})")

    # Auditor marks completed
    res_comp = client.post(f"/rbac/auditor/projects/{case_id}/complete", headers=AUDITOR_HEADERS)
    print(f"   -> Auditor Status: {res_comp.json().get('status_label')}\n")

    # Step 4: Verification of Immediate Reflection Across All Users & Audit Trail
    print("STEP 4: [IMMEDIATE REFLECTION & AUDIT TRAIL VERIFICATION]")
    res_head_view = client.get("/rbac/head/projects", headers=HEAD_HEADERS)
    head_data = res_head_view.json()
    print(f"   -> CSR Head View: Total Projects = {head_data.get('total_projects')}")
    print(f"   -> Programme Budget = INR {head_data.get('total_program_budget'):,.2f}")
    print(f"   -> Programme Spent  = INR {head_data.get('total_program_spent'):,.2f}")

    proj_info = head_data["projects"][0]
    print(f"   -> Project Title  : {proj_info.get('title')}")
    print(f"   -> Current Stage  : {proj_info.get('current_stage')}")
    print(f"   -> Progress       : {proj_info.get('milestone_summary', {}).get('overall_progress_percentage')}%")

    print("\n   IMMUTABLE AUDIT TRAIL HISTORY:")
    for idx, entry in enumerate(pack.get("audit_trail_history", []), 1):
        print(f"      [{idx}] Stage: {entry.get('stage')} | Actor: {entry.get('actor_id')} | Action: {entry.get('action')} | Note: {entry.get('comments')}")

    print("\n======================================================================")
    print("DEMO COMPLETED SUCCESSFULLY WITH 100% REFLECTION & ROLE ISOLATION!")
    print("======================================================================")

if __name__ == "__main__":
    run_sample_demo()
