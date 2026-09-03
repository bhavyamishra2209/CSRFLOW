"""
Tests for CSR document type definitions and helper functions.
"""

from document.schemas.document_types import (
    DOCUMENT_TYPES,
    CSR_DOCUMENT_TYPES,
    is_csr_type,
    get_document_type_list,
)


def test_total_document_types_count():
    assert len(DOCUMENT_TYPES) == 20, f"Expected 20 document types, got {len(DOCUMENT_TYPES)}"


def test_csr_document_types_list():
    assert len(CSR_DOCUMENT_TYPES) == 10
    expected_csr = [
        "Project Proposal",
        "Budget Sheet",
        "Progress Report",
        "Utilization Certificate",
        "Completion Report",
        "Compliance Certificate",
        "Partnership Agreement",
        "Audit Report",
        "Impact Assessment Report",
        "CSR Policy Document",
    ]
    for doc_type in expected_csr:
        assert doc_type in CSR_DOCUMENT_TYPES


def test_is_csr_type_helper():
    assert is_csr_type("Project Proposal") is True
    assert is_csr_type("utilization certificate") is True
    assert is_csr_type("CSR Policy Document") is True
    assert is_csr_type("Application") is False
    assert is_csr_type("Invoice") is False
    assert is_csr_type("Unknown") is False
    assert is_csr_type("") is False
    assert is_csr_type(None) is False


def test_get_document_type_list():
    type_list = get_document_type_list()
    assert len(type_list) == 20
    assert "Project Proposal" in type_list
    assert "Identity Proof" in type_list
