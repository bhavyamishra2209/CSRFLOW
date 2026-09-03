"""
Tests for CSR Duplicate & Statutory Compliance Checker Engine and API Routes.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from compliance.duplicate_checker import DuplicateChecker, calculate_text_hash, calculate_fuzzy_similarity
from compliance.compliance_verifier import (
    StatutoryComplianceVerifier,
    verify_section_135_eligibility,
    verify_schedule_vii_alignment,
    verify_ca_and_csr1_credentials,
)
from routes.routes import _DOC_REGISTRY
from routes.case_routes import _CASE_REGISTRY

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


def test_text_hash_and_similarity():
    """Test text hashing and fuzzy similarity functions."""
    t1 = "Project Proposal for Rural Clean Drinking Water in Rajasthan"
    t2 = "Project Proposal for Rural Clean Drinking Water in Rajasthan"
    t3 = "Project Proposal for Clean Water Supply in Rajasthan villages"

    assert calculate_text_hash(t1) == calculate_text_hash(t2)
    assert calculate_fuzzy_similarity(t1, t2) == 1.0
    assert calculate_fuzzy_similarity(t1, t3) > 0.6


def test_exact_and_fuzzy_duplicate_detection():
    """Test exact and fuzzy duplicate detection against doc registry."""
    text1 = "Utilization Certificate for Solar Micro-Grid Project Phase 1"
    
    _DOC_REGISTRY["DOC-001"] = {
        "document_id": "DOC-001",
        "filename": "uc_solar.pdf",
        "raw_text_preview": text1,
        "text_hash": calculate_text_hash(text1),
    }

    # Exact duplicate check
    is_exact, match_exact = DuplicateChecker.check_exact_duplicate(text1, _DOC_REGISTRY)
    assert is_exact is True
    assert match_exact["document_id"] == "DOC-001"

    # Fuzzy duplicate check
    text_fuzzy = "Utilization Certificate for Solar Micro Grid Project Phase 1"
    is_fuzzy, score, match_fuzzy = DuplicateChecker.check_fuzzy_duplicate(text_fuzzy, _DOC_REGISTRY, threshold=0.8)
    assert is_fuzzy is True
    assert score >= 0.8
    assert match_fuzzy["document_id"] == "DOC-001"


def test_double_funding_claim_detection():
    """Test detecting duplicate UC numbers and double funding claims."""
    _DOC_REGISTRY["DOC-002"] = {
        "document_id": "DOC-002",
        "filename": "uc_report_donorA.pdf",
        "extracted_fields": [
            {"field": "uc_number", "value": "UC/CSR/2026/099"},
            {"field": "project_title", "value": "Clean Water Initiative"},
            {"field": "total_budget", "value": "5000000"},
        ],
    }

    # Duplicate UC test
    fields_duplicate_uc = [{"field": "uc_number", "value": "UC/CSR/2026/099"}]
    is_dup1, claims1 = DuplicateChecker.check_double_funding_claim(fields_duplicate_uc, _DOC_REGISTRY)
    assert is_dup1 is True
    assert claims1[0]["reason"] == "DUPLICATE_UC_NUMBER"

    # Double funding title + budget test
    fields_double_funding = [
        {"field": "project_title", "value": "Clean Water Initiative"},
        {"field": "total_budget", "value": "5000000"},
    ]
    is_dup2, claims2 = DuplicateChecker.check_double_funding_claim(fields_double_funding, _DOC_REGISTRY)
    assert is_dup2 is True
    assert claims2[0]["reason"] == "DOUBLE_FUNDING_CLAIM"


def test_section_135_eligibility_calculator():
    """Test Companies Act Section 135 2% net profit rule calculation."""
    # Eligible company with sufficient CSR allocation
    r1 = verify_section_135_eligibility(
        average_net_profit=100000000.0, # Rs 10 Crore
        allocated_csr_budget=2500000.0,  # Rs 25 Lakhs (Required is Rs 20 Lakhs = 2%)
    )
    assert r1["is_section_135_eligible"] is True
    assert r1["required_min_csr_budget_2_percent"] == 2000000.0
    assert r1["meets_2_percent_rule"] is True
    assert r1["shortfall_amount"] == 0.0

    # Shortfall company
    r2 = verify_section_135_eligibility(
        average_net_profit=100000000.0,
        allocated_csr_budget=1000000.0,  # Rs 10 Lakhs (Shortfall of 10 Lakhs)
    )
    assert r2["meets_2_percent_rule"] is False
    assert r2["shortfall_amount"] == 1000000.0


def test_schedule_vii_alignment():
    """Test Schedule VII category keyword matching."""
    obj1 = "Providing clean solar drinking water pumps and sanitation units in villages"
    sch1 = verify_schedule_vii_alignment(obj1)
    assert sch1["is_aligned"] is True
    assert "HUNGER_HEALTH_WATER" in [c["category_key"] for c in sch1["matched_categories"]] or "ENVIRONMENT_SUSTAINABILITY" in [c["category_key"] for c in sch1["matched_categories"]]

    obj2 = "Promoting secondary school education and vocational skill development for youth"
    sch2 = verify_schedule_vii_alignment(obj2)
    assert sch2["is_aligned"] is True
    assert "EDUCATION_SKILLS" in [c["category_key"] for c in sch2["matched_categories"]]


def test_credentials_format_checker():
    """Test CA FRN and Form CSR-1 credential validation."""
    c1 = verify_ca_and_csr1_credentials(ca_frn="104928W", csr1_number="CSR00012345")
    assert c1["ca_frn_valid"] is True
    assert c1["csr1_registration_valid"] is True

    c2 = verify_ca_and_csr1_credentials(ca_frn="INVALID_FRN", csr1_number="123")
    assert c2["ca_frn_valid"] is False
    assert c2["csr1_registration_valid"] is False


def test_compliance_report_generator():
    """Test overall compliance report score and risk levels."""
    rep_clean = StatutoryComplianceVerifier.generate_compliance_report(
        project_title="Rural Drinking Water Initiative",
        objectives="Providing clean drinking water filtration in rural schools",
        allocated_csr_budget=2000000.0,
        average_net_profit=100000000.0,
        ca_frn="104928W",
        csr1_number="CSR00012345",
        duplicate_flagged=False,
    )
    assert rep_clean["compliance_score"] >= 85.0
    assert rep_clean["status"] == "FULLY_COMPLIANT"
    assert rep_clean["risk_level"] == "LOW"

    rep_dup = StatutoryComplianceVerifier.generate_compliance_report(
        project_title="Duplicate Claim Test",
        objectives="School renovation",
        allocated_csr_budget=500000.0,
        duplicate_flagged=True,
    )
    assert rep_dup["status"] == "FLAGGED_DUPLICATE"
    assert rep_dup["risk_level"] == "CRITICAL"


def test_compliance_api_endpoints():
    """Test compliance API endpoints end-to-end."""
    # 1. POST /compliance/check-duplicate
    res_dup = client.post(
        "/compliance/check-duplicate",
        headers=AUTH_HEADERS,
        json={"raw_text": "Sample project proposal text for duplicate testing"},
    )
    assert res_dup.status_code == 200
    assert "is_duplicate_flagged" in res_dup.json()

    # 2. POST /compliance/check-document
    res_doc = client.post(
        "/compliance/check-document",
        headers=AUTH_HEADERS,
        json={
            "project_title": "Solar Powered School Electrification",
            "objectives": "Install solar panels and digital classrooms in rural primary schools",
            "allocated_csr_budget": 2000000.0,
            "average_net_profit": 100000000.0,
            "ca_frn": "104928W",
            "csr1_number": "CSR00012345",
        },
    )
    assert res_doc.status_code == 200
    data_doc = res_doc.json()
    assert data_doc["status"] == "FULLY_COMPLIANT"
    assert data_doc["compliance_score"] >= 85.0

    # 3. POST /compliance/verify-case
    case_id = "CASE-COMP-900"
    client.post("/cases", headers=AUTH_HEADERS, json={"case_id": case_id, "title": "Compliance Test Project"})
    
    res_case = client.post(
        "/compliance/verify-case",
        headers=AUTH_HEADERS,
        json={
            "case_id": case_id,
            "allocated_csr_budget": 3000000.0,
            "average_net_profit": 150000000.0,
        },
    )
    assert res_case.status_code == 200
    assert res_case.json()["case_id"] == case_id

    # 4. GET /cases/{case_id}/compliance-report
    res_rep = client.get(f"/cases/{case_id}/compliance-report", headers=AUTH_HEADERS)
    assert res_rep.status_code == 200
    assert "compliance_score" in res_rep.json()
