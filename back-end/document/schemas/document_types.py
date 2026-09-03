"""
Document type definitions and descriptions for classification.
P2 requirement: 8-10 document types with descriptions.
"""

from typing import Dict, List

# Document type definitions with descriptions for embedding-based classification
DOCUMENT_TYPES = {
    "APPLICATION": {
        "name": "Application",
        "description": "Government application forms, job applications, permit applications, license applications, registration forms, application for benefits, service request forms",
        "keywords": ["application", "form", "applicant", "apply", "request", "registration", "enrollment"]
    },
    "IDENTITY_PROOF": {
        "name": "Identity Proof",
        "description": "Identity documents including Aadhaar card, PAN card, passport, driver's license, voter ID card, national ID, employee ID, student ID",
        "keywords": ["aadhaar", "pan", "passport", "license", "voter", "identity", "identification", "ID card"]
    },
    "ADDRESS_PROOF": {
        "name": "Address Proof",
        "description": "Address verification documents including utility bills, bank statements, rental agreements, property documents, ration card, domicile certificate",
        "keywords": ["address", "residence", "domicile", "utility bill", "electricity", "water bill", "rental", "lease"]
    },
    "AFFIDAVIT": {
        "name": "Affidavit",
        "description": "Sworn statements, affidavits, statutory declarations, notarized statements, oath documents, legal declarations",
        "keywords": ["affidavit", "sworn", "oath", "declare", "notary", "notarized", "solemnly", "affirm"]
    },
    "CERTIFICATE": {
        "name": "Certificate",
        "description": "Certificates including birth certificate, death certificate, marriage certificate, educational certificates, experience certificates, caste certificate, income certificate",
        "keywords": ["certificate", "certify", "certified", "hereby certify", "issued", "attestation"]
    },
    "COURT_DOCUMENT": {
        "name": "Court Document",
        "description": "Court orders, judgments, summons, petitions, court notices, legal proceedings, case documents, court rulings",
        "keywords": ["court", "judge", "honorable", "petition", "plaintiff", "defendant", "case", "judgment", "order"]
    },
    "INVOICE": {
        "name": "Invoice",
        "description": "Invoices, bills, receipts, payment requests, purchase orders, proforma invoices, tax invoices, billing statements",
        "keywords": ["invoice", "bill", "amount", "total", "payment", "due", "GST", "tax", "purchase"]
    },
    "CONTRACT": {
        "name": "Contract",
        "description": "Contracts, agreements, memorandums of understanding (MOU), service agreements, employment contracts, lease agreements, terms and conditions",
        "keywords": ["contract", "agreement", "party", "parties", "terms", "conditions", "hereby agree", "MOU"]
    },
    "RECEIPT": {
        "name": "Receipt",
        "description": "Payment receipts, acknowledgment receipts, transaction confirmations, proof of payment, fee receipts",
        "keywords": ["receipt", "received", "acknowledgment", "paid", "transaction", "confirmation", "ref no"]
    },
    "OTHER": {
        "name": "Other",
        "description": "Miscellaneous documents, letters, notices, memos, reports, statements that don't fit other categories",
        "keywords": ["document", "letter", "notice", "memo", "report", "statement"]
    },
    # ── CSR Document Types ─────────────────────────────────────────
    "PROJECT_PROPOSAL": {
        "name": "Project Proposal",
        "description": "CSR project proposal document detailing implementing agency, target beneficiaries, total budget, project duration, objectives, location, and CSR schedule",
        "keywords": ["project proposal", "implementing agency", "target beneficiaries", "total budget", "project duration", "objectives", "csr schedule", "proposal"]
    },
    "BUDGET_SHEET": {
        "name": "Budget Sheet",
        "description": "CSR project financial budget sheet detailing allocated budget, spent amount, unspent amount, financial year, and category-wise budget allocations",
        "keywords": ["budget sheet", "financial year", "allocated budget", "spent amount", "unspent amount", "budget categories", "csr budget"]
    },
    "PROGRESS_REPORT": {
        "name": "Progress Report",
        "description": "CSR project periodic progress report tracking milestones achieved, funds utilized, beneficiary count, reporting period, and project challenges",
        "keywords": ["progress report", "reporting period", "milestones achieved", "funds utilized", "beneficiary count", "csr progress"]
    },
    "UTILIZATION_CERTIFICATE": {
        "name": "Utilization Certificate",
        "description": "CSR utilization certificate (UC) certifying proper utilization of CSR funds signed by a chartered accountant with UC number, certified amount, and percentage",
        "keywords": ["utilization certificate", "uc number", "certified amount", "utilization percentage", "chartered accountant", "csr uc", "funds utilized"]
    },
    "COMPLETION_REPORT": {
        "name": "Completion Report",
        "description": "CSR project final completion report detailing project completion date, final cost, target achieved, impact summary, and final project outcomes",
        "keywords": ["completion report", "completion date", "final cost", "target achieved", "impact summary", "project completed"]
    },
    "COMPLIANCE_CERTIFICATE": {
        "name": "Compliance Certificate",
        "description": "CSR statutory compliance certificate confirming compliance with CSR provisions, Companies Act rules, financial year compliance status, and authorized signatures",
        "keywords": ["compliance certificate", "compliance status", "companies act", "csr compliance", "statutory compliance", "issue date"]
    },
    "PARTNERSHIP_AGREEMENT": {
        "name": "Partnership Agreement",
        "description": "CSR partnership agreement or Memorandum of Understanding (MOU) between corporate entity and implementing agency / partner organization",
        "keywords": ["partnership agreement", "partner organization", "implementing agency", "funding amount", "validity period", "mou", "csr agreement"]
    },
    "AUDIT_REPORT": {
        "name": "Audit Report",
        "description": "CSR financial and governance audit report issued by an independent auditor detailing audit opinion, audit report number, financial year, and findings",
        "keywords": ["audit report", "auditor name", "audit opinion", "audit date", "csr audit", "independent auditor", "audit report number"]
    },
    "IMPACT_ASSESSMENT_REPORT": {
        "name": "Impact Assessment Report",
        "description": "CSR social impact assessment report evaluating project outcomes, assessing agency, impact score, key findings, assessment period, and beneficiary feedback",
        "keywords": ["impact assessment report", "assessing agency", "impact score", "key findings", "assessment period", "social impact", "csr impact"]
    },
    "CSR_POLICY_DOCUMENT": {
        "name": "CSR Policy Document",
        "description": "Corporate CSR policy document outlining corporate social responsibility vision, focus areas, CSR committee members, approval date, and policy version",
        "keywords": ["csr policy document", "policy version", "csr vision", "focus areas", "csr committee", "approval date", "csr policy"]
    }
}

CSR_DOCUMENT_TYPES = [
    "Project Proposal",
    "Budget Sheet",
    "Progress Report",
    "Utilization Certificate",
    "Completion Report",
    "Compliance Certificate",
    "Partnership Agreement",
    "Audit Report",
    "Impact Assessment Report",
    "CSR Policy Document"
]


def is_csr_type(document_type: str) -> bool:
    """
    Check whether a given document type string corresponds to a CSR document type.
    Case-insensitive matching is supported.
    """
    if not document_type:
        return False
    doc_type_lower = document_type.strip().lower()
    return any(csr_type.lower() == doc_type_lower for csr_type in CSR_DOCUMENT_TYPES)


def get_document_type_list() -> List[str]:
    """Get list of all document type names."""
    return [dt["name"] for dt in DOCUMENT_TYPES.values()]


def get_document_type_descriptions() -> Dict[str, str]:
    """Get mapping of document type names to descriptions."""
    return {dt["name"]: dt["description"] for dt in DOCUMENT_TYPES.values()}


def get_document_type_keywords() -> Dict[str, List[str]]:
    """Get mapping of document type names to keywords."""
    return {dt["name"]: dt["keywords"] for dt in DOCUMENT_TYPES.values()}


def get_all_document_types() -> Dict[str, Dict]:
    """Get complete document type definitions."""
    return {key: value for key, value in DOCUMENT_TYPES.items()}

