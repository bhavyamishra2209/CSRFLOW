"""
CSR Duplicate & Statutory Compliance API Routes.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.auth import get_current_user, UserInfo
from routes.routes import _DOC_REGISTRY
from routes.case_routes import _CASE_REGISTRY
from compliance.duplicate_checker import DuplicateChecker
from compliance.compliance_verifier import StatutoryComplianceVerifier, verify_section_135_eligibility

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["CSR Duplicate & Compliance Checker"])


class DuplicateCheckInput(BaseModel):
    raw_text: Optional[str] = Field(default="", description="Document text for similarity matching")
    extracted_fields: Optional[List[Dict[str, Any]]] = Field(default=None, description="Extracted key-value fields")
    exclude_document_id: Optional[str] = Field(default=None, description="Current document ID to exclude")


class ComplianceCheckInput(BaseModel):
    case_id: str = Field(description="CSR Case ID to verify")
    average_net_profit: Optional[float] = Field(default=0.0, description="Preceding 3-year average net profit")
    allocated_csr_budget: Optional[float] = Field(default=0.0, description="Allocated CSR budget for this project")
    ca_frn: Optional[str] = Field(default=None, description="CA Firm Registration Number (e.g. 104928W)")
    csr1_number: Optional[str] = Field(default=None, description="Form CSR-1 Registration Number (e.g. CSR00012345)")


class SingleDocumentCheckInput(BaseModel):
    project_title: str = Field(description="Project or document title")
    objectives: Optional[str] = Field(default="", description="Project objectives description")
    raw_text: Optional[str] = Field(default="", description="Raw text content")
    extracted_fields: Optional[List[Dict[str, Any]]] = Field(default=None, description="Extracted fields")
    allocated_csr_budget: Optional[float] = Field(default=0.0, description="Allocated CSR budget")
    average_net_profit: Optional[float] = Field(default=0.0, description="Preceding 3-year average net profit")
    ca_frn: Optional[str] = Field(default=None, description="CA FRN number")
    csr1_number: Optional[str] = Field(default=None, description="Form CSR-1 number")


@router.post("/check-duplicate", summary="Scan text or fields for duplicates and double funding")
async def check_duplicate_endpoint(
    data: DuplicateCheckInput,
    user: UserInfo = Depends(get_current_user),
):
    """Scan document text or extracted fields for exact/fuzzy duplicates and double-funding claims."""
    raw_text = data.raw_text or ""
    exclude_id = data.exclude_document_id

    # 1. Exact Duplicate Hash Match
    is_exact, exact_doc = DuplicateChecker.check_exact_duplicate(raw_text, _DOC_REGISTRY, exclude_doc_id=exclude_id)

    # 2. Fuzzy Similarity Match
    is_fuzzy, fuzzy_score, fuzzy_doc = DuplicateChecker.check_fuzzy_duplicate(raw_text, _DOC_REGISTRY, threshold=0.85, exclude_doc_id=exclude_id)

    # 3. Double Funding Claim Match
    is_double_funded, funding_claims = DuplicateChecker.check_double_funding_claim(data.extracted_fields or [], _DOC_REGISTRY, exclude_doc_id=exclude_id)

    is_flagged = is_exact or is_fuzzy or is_double_funded

    return {
        "is_duplicate_flagged": is_flagged,
        "exact_duplicate_found": is_exact,
        "exact_matched_doc_id": exact_doc.get("document_id") if exact_doc else None,
        "fuzzy_duplicate_found": is_fuzzy,
        "fuzzy_similarity_score": round(fuzzy_score, 2),
        "fuzzy_matched_doc_id": fuzzy_doc.get("document_id") if fuzzy_doc else None,
        "double_funding_claims_found": is_double_funded,
        "funding_claim_details": funding_claims,
    }


@router.post("/verify-case", summary="Run statutory compliance & duplicate verification on a case")
async def verify_case_compliance_endpoint(
    data: ComplianceCheckInput,
    user: UserInfo = Depends(get_current_user),
):
    """Verify Section 135 Companies Act compliance, Schedule VII alignment, and duplicates for a case."""
    case = _CASE_REGISTRY.get(data.case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": data.case_id},
        )

    doc_ids = case.get("document_ids", [])
    case_title = case.get("title", f"Case {data.case_id}")
    
    # Aggregate text and fields from attached documents
    all_text = []
    all_fields = []
    
    for did in doc_ids:
        doc = _DOC_REGISTRY.get(did)
        if doc:
            if doc.get("raw_text_preview"):
                all_text.append(doc["raw_text_preview"])
            if doc.get("extracted_fields"):
                all_fields.extend(doc["extracted_fields"])

    combined_text = case_title + "\n" + "\n".join(all_text)

    # Run duplicate scan across registry
    is_double_funded, funding_claims = DuplicateChecker.check_double_funding_claim(all_fields, _DOC_REGISTRY)

    # Generate statutory compliance report
    report = StatutoryComplianceVerifier.generate_compliance_report(
        project_title=case_title,
        objectives=combined_text,
        allocated_csr_budget=data.allocated_csr_budget or 0.0,
        average_net_profit=data.average_net_profit or 0.0,
        ca_frn=data.ca_frn,
        csr1_number=data.csr1_number,
        duplicate_flagged=is_double_funded,
    )

    # Attach duplicate details
    report["double_funding_claims"] = funding_claims
    report["case_id"] = data.case_id
    report["attached_document_count"] = len(doc_ids)

    # Cache compliance report on case object
    case["compliance_report"] = report
    _CASE_REGISTRY[data.case_id] = case

    return report


@router.post("/check-document", summary="Combined duplicate and compliance verification on a document")
async def check_single_document_compliance(
    data: SingleDocumentCheckInput,
    user: UserInfo = Depends(get_current_user),
):
    """Run combined single-call duplicate detection and Section 135 / Schedule VII compliance check."""
    raw_text = data.raw_text or data.objectives or data.project_title

    # 1. Duplicate scan
    is_exact, exact_doc = DuplicateChecker.check_exact_duplicate(raw_text, _DOC_REGISTRY)
    is_fuzzy, fuzzy_score, fuzzy_doc = DuplicateChecker.check_fuzzy_duplicate(raw_text, _DOC_REGISTRY, threshold=0.85)
    is_double_funded, funding_claims = DuplicateChecker.check_double_funding_claim(data.extracted_fields or [], _DOC_REGISTRY)

    is_duplicate_flagged = is_exact or is_fuzzy or is_double_funded

    # 2. Compliance evaluation
    report = StatutoryComplianceVerifier.generate_compliance_report(
        project_title=data.project_title,
        objectives=data.objectives or raw_text,
        allocated_csr_budget=data.allocated_csr_budget or 0.0,
        average_net_profit=data.average_net_profit or 0.0,
        ca_frn=data.ca_frn,
        csr1_number=data.csr1_number,
        duplicate_flagged=is_duplicate_flagged,
    )

    report["duplicate_scan"] = {
        "is_duplicate_flagged": is_duplicate_flagged,
        "exact_duplicate": is_exact,
        "fuzzy_duplicate": is_fuzzy,
        "fuzzy_similarity_score": round(fuzzy_score, 2),
        "double_funding_claims": funding_claims,
    }

    return report


# Additional GET endpoint for case compliance report under /cases
case_compliance_router = APIRouter(prefix="/cases", tags=["CSR Duplicate & Compliance Checker"])


@case_compliance_router.get("/{case_id}/compliance-report", summary="Get stored compliance report for a case")
async def get_case_compliance_report(
    case_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Get stored statutory compliance and duplicate report for a case."""
    case = _CASE_REGISTRY.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Case not found", "case_id": case_id},
        )

    report = case.get("compliance_report")
    if not report:
        # Generate default baseline report
        report = StatutoryComplianceVerifier.generate_compliance_report(
            project_title=case.get("title", f"Case {case_id}"),
            objectives=case.get("title", ""),
            allocated_csr_budget=0.0,
        )
        report["case_id"] = case_id

    return report


def register_compliance_routes(app: FastAPI) -> None:
    """Register compliance routes on FastAPI app."""
    app.include_router(router)
    app.include_router(case_compliance_router)
    logger.info("✓ CSR Duplicate & Compliance routes registered: /compliance/* and /cases/{id}/compliance-report")
