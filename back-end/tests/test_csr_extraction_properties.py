"""
Tests for CSR extraction field coverage, duplicate prevention, and evidence tracking.
"""

import pytest
from document.field_extractor import FieldExtractor


class MockRAGEngine:
    pass


def test_no_duplicate_field_names_in_extraction():
    extractor = FieldExtractor(MockRAGEngine())
    text = "Project Title: Clean Water Initiative\nTotal Budget: 1250000"
    chunks = [text]
    metadata = [{"page": 1}]

    fields = extractor.extract(chunks, metadata, "Project Proposal", "proposal.pdf")

    field_names = [f["field"] for f in fields]
    assert len(field_names) == len(set(field_names)), "Found duplicate field names in extraction result"


def test_evidence_structure_in_extracted_fields():
    extractor = FieldExtractor(MockRAGEngine())
    text = "Project Title: Clean Water Initiative\nTotal Budget: INR 1250000"
    chunks = [text]
    metadata = [{"page": 1}]

    fields = extractor.extract(chunks, metadata, "Project Proposal", "proposal.pdf")

    title_field = next((f for f in fields if f["field"] == "project_title"), None)
    assert title_field is not None
    assert title_field["value"] == "Clean Water Initiative"
    assert "evidence" in title_field
    ev = title_field["evidence"]
    assert "source_document" in ev
    assert "page" in ev
    assert "evidence_snippet" in ev
    assert "confidence" in ev
