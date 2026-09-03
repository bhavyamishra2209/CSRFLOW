"""
CSR context builder for post-upload document summaries.
"""

import logging
from typing import List, Dict, Any

from document.schemas.document_types import is_csr_type
from document.field_extractor import load_schema

logger = logging.getLogger(__name__)


def build_csr_context(
    document_type: str, 
    extracted_fields: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Build a summary of CSR document requirements and extraction results.

    Args:
        document_type: The document type string
        extracted_fields: List of extracted field dictionaries

    Returns:
        Dict representing csr_context structure for upload response.
    """
    if not is_csr_type(document_type):
        return {
            "is_csr_document": False
        }

    schema = load_schema(document_type)
    fields_def = schema.get("fields", [])

    required_fields = [
        f["name"] for f in fields_def 
        if isinstance(f, dict) and f.get("required") is True
    ]

    extracted_set = set()
    for item in extracted_fields:
        if isinstance(item, dict):
            field_name = item.get("field") or item.get("name")
            val = item.get("value")
            if field_name and val is not None and str(val).strip() != "":
                extracted_set.add(field_name)

    extracted_required = [f for f in required_fields if f in extracted_set]
    missing_required = [f for f in required_fields if f not in extracted_set]

    return {
        "is_csr_document": True,
        "csr_document_type": document_type,
        "required_fields": required_fields,
        "extracted_required_fields": extracted_required,
        "missing_required_fields": missing_required,
    }
