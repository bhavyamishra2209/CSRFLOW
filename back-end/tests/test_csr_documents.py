"""
End-to-end tests for CSR verifier scoring, CSR context generation, schema hot reload, and Project Proposal extraction.
"""

import pytest
from verification.csr_verifier import verify_csr_document
from document.csr_context import build_csr_context
from document.schema_store import schema_store
from document.field_extractor import FieldExtractor


class MockRAGEngine:
    pass


def test_csr_verifier_completeness_scoring():
    # Complete document
    extracted_complete = [
        {"field": "project_title", "value": "Clean Water Initiative"},
        {"field": "implementing_agency", "value": "River NGO"},
        {"field": "total_budget", "value": "1250000"},
        {"field": "project_duration", "value": "12 months"},
        {"field": "submission_date", "value": "15/04/2026"},
    ]
    res_comp = verify_csr_document(extracted_complete, "Project Proposal")
    assert res_comp["status"] == "complete"
    assert res_comp["confidence"] == 1.0
    assert len(res_comp["missing_fields"]) == 0

    # Incomplete document
    extracted_incomplete = [
        {"field": "project_title", "value": "Clean Water Initiative"},
        {"field": "total_budget", "value": "1250000"},
    ]
    res_incomp = verify_csr_document(extracted_incomplete, "Project Proposal")
    assert res_incomp["status"] == "incomplete"
    assert res_incomp["confidence"] < 1.0
    assert len(res_incomp["missing_fields"]) > 0
    assert "implementing_agency" in res_incomp["missing_fields"]


def test_build_csr_context():
    extracted = [
        {"field": "project_title", "value": "Clean Water Initiative"},
        {"field": "total_budget", "value": "1250000"},
    ]
    ctx_csr = build_csr_context("Project Proposal", extracted)
    assert ctx_csr["is_csr_document"] is True
    assert ctx_csr["csr_document_type"] == "Project Proposal"
    assert "project_title" in ctx_csr["extracted_required_fields"]
    assert "implementing_agency" in ctx_csr["missing_required_fields"]

    ctx_non_csr = build_csr_context("Application", extracted)
    assert ctx_non_csr["is_csr_document"] is False


def test_schema_hot_reload():
    schema_before = schema_store.get_schema("Project Proposal")
    assert schema_before is not None
    initial_count = len(schema_before["fields"])

    # Force a reload
    schema_store.reload()
    schema_after = schema_store.get_schema("Project Proposal")
    assert len(schema_after["fields"]) == initial_count


def test_project_proposal_extraction_example():
    text = (
        "Project Title: Clean Water Initiative\n"
        "Implementing Agency: River NGO\n"
        "Total Budget: INR 1250000\n"
        "Submission Date: 15/04/2026\n"
    )
    extractor = FieldExtractor(MockRAGEngine())
    fields = extractor.extract([text], [{"page": 1}], "Project Proposal", "proposal.pdf")

    extracted_dict = {f["field"]: f["value"] for f in fields}

    assert extracted_dict.get("project_title") == "Clean Water Initiative"
    assert extracted_dict.get("implementing_agency") == "River NGO"
    assert extracted_dict.get("total_budget") == "1250000"
    assert extracted_dict.get("submission_date") == "15/04/2026"
