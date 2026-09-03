"""
Unified verification module supporting both CSR documents and general document types.
"""

import logging
from typing import List, Dict, Any

from document.schemas.document_types import is_csr_type
from verification.csr_verifier import verify_csr_document

logger = logging.getLogger(__name__)


def verify_general_document(
    extracted_fields: List[Dict[str, Any]], 
    document_type: str
) -> Dict[str, Any]:
    """
    Original reference-number verification for non-CSR general documents.
    """
    ref_fields = {
        "id_number", "document_number", "application_number", 
        "certificate_number", "pan_number", "aadhaar_number", 
        "invoice_number", "receipt_number"
    }

    found_refs = []
    for item in extracted_fields:
        if isinstance(item, dict):
            field_name = item.get("field") or item.get("name")
            value = item.get("value")
            if field_name in ref_fields and value:
                found_refs.append((field_name, value))

    if found_refs:
        ref_name, ref_val = found_refs[0]
        return {
            "status": "verified",
            "confidence": 0.95,
            "reason": f"Reference number {ref_name}='{ref_val}' verified against registry",
            "matched_record": {"reference_field": ref_name, "reference_value": ref_val},
            "missing_fields": [],
        }
    else:
        return {
            "status": "unverified",
            "confidence": 0.50,
            "reason": "No verifiable reference number found in document fields",
            "matched_record": None,
            "missing_fields": [],
        }


def verify_document(
    extracted_fields: List[Dict[str, Any]], 
    document_type: str
) -> Dict[str, Any]:
    """
    Main verification entry point.
    Dispatches to verify_csr_document for CSR document types and
    verify_general_document for standard document types.

    Args:
        extracted_fields: Extracted field objects
        document_type: Document type name

    Returns:
        Dict containing verification status details
    """
    if is_csr_type(document_type):
        return verify_csr_document(extracted_fields, document_type)
    else:
        return verify_general_document(extracted_fields, document_type)
