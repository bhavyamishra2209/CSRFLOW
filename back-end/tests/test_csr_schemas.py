"""
Tests for CSR JSON schema files.
"""

import json
from pathlib import Path
from document.schema_store import schema_store


SCHEMA_DIR = Path(__file__).parent.parent / "document" / "schemas"

CSR_SCHEMA_FILES = [
    "project_proposal.json",
    "budget_sheet.json",
    "progress_report.json",
    "utilization_certificate.json",
    "completion_report.json",
    "compliance_certificate.json",
    "partnership_agreement.json",
    "audit_report.json",
    "impact_assessment_report.json",
    "csr_policy_document.json",
]


def test_csr_schema_files_exist():
    for filename in CSR_SCHEMA_FILES:
        path = SCHEMA_DIR / filename
        assert path.exists(), f"Schema file missing: {filename}"


def test_csr_schema_content_structure():
    for filename in CSR_SCHEMA_FILES:
        path = SCHEMA_DIR / filename
        data = json.loads(path.read_text(encoding="utf-8"))

        assert "document_type" in data
        assert "description" in data
        assert "fields" in data
        assert isinstance(data["fields"], list)
        assert len(data["fields"]) > 0

        for field in data["fields"]:
            assert "name" in field
            assert "type" in field
            assert "description" in field
            assert "required" in field
            assert field["type"] in {"string", "date", "number", "boolean", "email", "phone"}


def test_project_proposal_schema_fields():
    schema = schema_store.get_schema("Project Proposal")
    assert schema is not None
    field_names = [f["name"] for f in schema["fields"]]
    expected_fields = [
        "project_title",
        "implementing_agency",
        "target_beneficiaries",
        "total_budget",
        "project_duration",
        "project_location",
        "objectives",
        "csr_schedule",
        "contact_person",
        "submission_date",
    ]
    for ef in expected_fields:
        assert ef in field_names
