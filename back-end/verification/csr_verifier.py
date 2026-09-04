"""
CSR document completeness verification.
Evaluates CSR documents against schema-defined required fields.
"""

import logging
from typing import List, Dict, Any

from document.field_extractor import load_schema

logger = logging.getLogger(__name__)


def verify_csr_document(
    extracted_fields: List[Dict[str, Any]], 
    document_type: str
) -> Dict[str, Any]:
    """
    Verify CSR document based on required field completeness.

    Args:
        extracted_fields: List of field dicts extracted from document
        document_type: The CSR document type name

    Returns:
        Dict containing status, confidence, missing_fields, and reason.
    """
    schema = load_schema(document_type)
    fields_def = schema.get("fields", [])

    # Identify required fields from schema
    required_field_names = [
        f["name"] for f in fields_def 
        if isinstance(f, dict) and f.get("required") is True
    ]

    # Map extracted fields having non-null, non-empty values
    present_field_names = set()
    for item in extracted_fields:
        if isinstance(item, dict):
            field_name = item.get("field") or item.get("name")
            value = item.get("value")
            if field_name and value is not None and str(value).strip() != "":
                present_field_names.add(field_name)

    # Determine missing required fields
    missing_fields = [fn for fn in required_field_names if fn not in present_field_names]

    total_required = len(required_field_names)
    missing_count = len(missing_fields)
    present_count = total_required - missing_count

    if total_required == 0 or missing_count == 0:
        status = "complete"
        confidence = 1.0
        reason = f"Verified: All {total_required if total_required > 0 else len(present_field_names)} required schema fields are present"
    else:
        status = "incomplete"
        confidence = round(present_count / total_required, 2) if total_required > 0 else 0.8
        reason = f"Needs Review: {missing_count} of {total_required} required fields are missing ({', '.join(missing_fields)})"

    matched_rec = {
        "document_type": document_type,
        "present_fields": list(present_field_names),
        "total_extracted": len(extracted_fields)
    }

    logger.info(
        f"CSR verification for '{document_type}': status={status}, "
        f"confidence={confidence}, missing={missing_fields}"
    )

    return {
        "status": status,
        "confidence": confidence,
        "missing_fields": missing_fields,
        "reason": reason,
        "matched_record": matched_rec,
    }
