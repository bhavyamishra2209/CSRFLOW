"""
Enhanced field extraction module with schema-based extraction.
P3 requirement: Config-based JSON schemas per document type.
P4 requirement: Evidence tracking for every extracted field.
"""

import json
import os
import re
import logging
from typing import List, Dict, Any, Optional

from document.evidence_tracker import EvidenceTracker, create_extracted_field, Evidence

logger = logging.getLogger(__name__)

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")


def load_schema(document_type: str) -> Dict[str, Any]:
    """
    Load JSON schema for a document type.
    Delegates to schema_store so PUT /schemas/{type} edits take effect
    immediately without restarting the server.
    """
    try:
        from document.schema_store import schema_store
        return schema_store.load_schema(document_type)
    except Exception as e:
        logger.warning(f"schema_store unavailable ({e}), falling back to direct file read")
        # ── Legacy fallback — direct file read ──────────────────────────────
        filename = document_type.lower().replace(" ", "_") + ".json"
        path = os.path.join(SCHEMA_DIR, filename)
        if not os.path.exists(path):
            logger.warning(f"Schema not found for document type: {document_type}")
            return {"fields": []}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as je:
            logger.error(f"Failed to parse schema {filename}: {je}")
            return {"fields": []}


class FieldExtractor:
    """
    Schema-based field extraction with LLM and evidence tracking.
    """
    
    def __init__(self, rag_engine):
        """
        Initialize field extractor.
        
        Args:
            rag_engine: RAG engine instance with LLM access
        """
        self.rag_engine = rag_engine
        self.evidence_tracker = EvidenceTracker()
    
    def extract(
        self, 
        chunks: List[str], 
        chunk_metadata: List[Dict[str, Any]], 
        document_type: str, 
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Extract structured fields from document chunks using schema.
        
        Args:
            chunks: List of text chunks from document
            chunk_metadata: Metadata for each chunk
            document_type: Type of document
            filename: Source filename
            
        Returns:
            List of extracted fields with evidence
        """
        # Load schema for document type
        schema = load_schema(document_type)
        fields = schema.get("fields", [])

        # Prepare text
        full_text = " ".join(chunks)[:4000]

        extracted_fields = []

        # ── Schema-based extraction (when schema exists) ─────────────────
        for field in fields:
            field_name = self._get_field_name(field)
            field_info = self._get_field_info(fields, field_name)

            value, confidence = self._extract_field_value(field_name, full_text)

            evidence = self.evidence_tracker.find_evidence(
                value, chunks, chunk_metadata, filename
            )

            extracted_field = create_extracted_field(
                field_name=field_name,
                value=value,
                confidence=confidence,
                evidence=evidence,
                field_type=field_info.get("type"),
                required=field_info.get("required")
            )
            extracted_fields.append(extracted_field.to_dict())

        # ── Universal fallback extraction ────────────────────────────────
        # Always runs — picks up whatever the schema missed or when no
        # schema exists. De-duplicates against schema results by reserving
        # all schema field names (even if value is None).
        schema_found_fields = {
            f["field"] for f in extracted_fields
        }
        universal = self._universal_extract(full_text)
        for field_name, value in universal.items():
            if field_name not in schema_found_fields:
                evidence = self.evidence_tracker.find_evidence(
                    value, chunks, chunk_metadata, filename
                )
                extracted_field = create_extracted_field(
                    field_name=field_name,
                    value=value,
                    confidence=0.85,
                    evidence=evidence,
                    field_type=self._guess_field_type(field_name),
                    required=False,
                )
                extracted_fields.append(extracted_field.to_dict())

        logger.info(f"Extracted {len(extracted_fields)} fields from {document_type}")
        return extracted_fields
    
    def _universal_extract(self, text: str) -> Dict[str, str]:
        """
        Schema-free extraction — works on ANY document type.

        Scans the text for key:value pairs using a broad set of patterns
        and returns whatever it finds as { field_name: value }.
        """
        results: Dict[str, str] = {}

        # ── Generic key:value pattern ──────────────────────────────────
        # Matches "Label: Value" or "Label - Value" lines
        kv_pattern = re.compile(
            r'^([A-Za-z][A-Za-z0-9 _/]{1,40}?)\s*[:\-]\s*(.{2,120}?)(?:\s*$)',
            re.MULTILINE
        )
        for m in kv_pattern.finditer(text):
            key_raw   = m.group(1).strip()
            value_raw = m.group(2).strip().rstrip('.,;')
            if not value_raw or len(value_raw) < 2:
                continue
            # Normalise key to snake_case
            key = re.sub(r'[\s/]+', '_', key_raw.lower())
            key = re.sub(r'[^a-z0-9_]', '', key)
            if key and value_raw:
                results[key] = value_raw

        # ── Specific universal patterns ────────────────────────────────
        universal_patterns = {
            # Dates — any label ending in "date" or "on"
            'date': r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b',
            # Email
            'email': r'\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b',
            # Phone (Indian + international)
            'phone': r'\b(\+?(?:91[\-\s]?)?\d{10})\b',
            # PAN card
            'pan_number': r'\b([A-Z]{5}\d{4}[A-Z])\b',
            # Aadhaar
            'aadhaar_number': r'\b(\d{4}\s\d{4}\s\d{4})\b',
            # Pincode
            'pincode': r'\b(\d{6})\b',
            # Currency amounts
            'amount': r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{2})?)',
            # Case / file numbers
            'case_number': r'(?:case|file|matter)\s*(?:no|number|#)\s*[:\-]?\s*([A-Z0-9\-/]{4,20})',
            # Court name
            'court': r'(?:in\s+the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Court|Tribunal|Commission|Board))',
            # Organisation / company
            'organization': r'\b([A-Z][A-Za-z\s&]+(?:Ltd|Limited|Pvt|Corporation|Corp|Inc|LLP|Authority|Board|Council)\.?)\b',
        }

        for field_name, pattern in universal_patterns.items():
            if field_name not in results:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    results[field_name] = m.group(1).strip()

        # ── Clean up noise keys ────────────────────────────────────────
        noise = {
            'the', 'and', 'or', 'of', 'to', 'in', 'a', 'an', 'is', 'it',
            'this', 'that', 'for', 'on', 'at', 'by', 'with', 'from',
        }
        return {
            k: v for k, v in results.items()
            if k not in noise and len(k) > 1 and len(v) > 1
        }

    @staticmethod
    def _guess_field_type(field_name: str) -> str:
        """Guess field type from field name."""
        name = field_name.lower()
        if any(x in name for x in ('date', 'dob', 'birth', 'issue', 'expiry', 'valid')):
            return 'date'
        if any(x in name for x in ('amount', 'fee', 'price', 'cost', 'salary', 'income')):
            return 'number'
        if 'email' in name:
            return 'email'
        if any(x in name for x in ('phone', 'mobile', 'contact', 'tel')):
            return 'phone'
        return 'string'

    def _extract_field_value(self, field_name: str, text: str) -> tuple:
        """
        Extract field value using improved pattern matching.
        
        Args:
            field_name: Name of field to extract
            text: Document text
            
        Returns:
            Tuple of (value, confidence)
        """
        # Define improved field patterns - covers both Application and Identity Proof types
        field_patterns = {
            # ── Identity / name fields ──────────────────────────────────
            'full_name': [
                r'(?:full\s+)?name\s*[:\-=]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\s+(?:ID|id|S/O|D/O|Age|DOB|Date|Address|Gender|\d)|\s*$)',
                r'(?:holder|bearer|applicant)\s+name\s*[:\-=]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\s+\S|\s*$)',
                r'(?:Mr|Ms|Mrs|Dr|Shri|Smt)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
            ],
            'holder_name': [
                r'(?:full\s+)?name\s*[:\-=]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\s+\S|\s*$)',
                r'holder\s*[:\-=]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
            ],
            'applicant_name': [
                r'(?:applicant\s+)?name\s*[:\-=]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\s+(?:ID|Date|DOB|Address|Age|\d)|\s*$)',
                r'(?:Mr|Ms|Mrs|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
            ],
            # ── ID / document numbers ────────────────────────────────────
            'document_number': [
                r'(?:id|identification|document)\s+(?:no|number|#)\s*[:\-=]\s*([A-Z0-9\-]{4,20})',
                r'(?:card|cert(?:ificate)?)\s+(?:no|number)\s*[:\-=]\s*([A-Z0-9\-/]{4,20})',
                r'(?:serial|sl)\s*(?:no|number)?\s*[:\-=]\s*([A-Z0-9\-]{4,20})',
                r'\b([A-Z]{2,4}[\-]?\d{4,12}(?:[\-][A-Z0-9]+)?)\b',
            ],
            'id_number': [
                r'(?:id|identification)\s+(?:no|number|#)\s*[:\-=]\s*([A-Z0-9\-]{4,20})',
                r'\b(ID[\-]?\d{4}[\-]\d{4}[\-]\d{4})\b',
                r'\b([A-Z]{2,4}[\-]\d{4,12})\b',
            ],
            'certificate_number': [
                r'cert(?:ificate)?\s+(?:no|number)\s*[:\-=]\s*([A-Z0-9\-/]{4,20})',
                r'\b([A-Z]{2,}\d{6,})\b',
            ],
            'application_number': [
                r'application\s+(?:no|number|#|num)\s*[:\-=]?\s*([A-Z0-9\-/]+)',
                r'reference\s+(?:no|number)\s*[:\-=]?\s*([A-Z0-9\-/]+)',
                r'\b([A-Z]{2,}\d{4,})\b',
            ],
            # ── Dates ────────────────────────────────────────────────────
            'date_of_birth': [
                r'date\s+of\s+birth\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'\bdob\b\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'born\s+on\s*[:\-=]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'birth\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'issue_date': [
                r'issue\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'issued\s+(?:on|date)\s*[:\-=]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'date\s+of\s+issue\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'valid\s+from\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'expiry_date': [
                r'(?:expiry|expiration|valid\s+until|valid\s+upto|valid\s+till)\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'expires?\s+(?:on)?\s*[:\-=]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'date_filed': [
                r'(?:application|filed|submission)\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'date\s+(?:filed|submitted)\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b',
            ],
            # ── Address ──────────────────────────────────────────────────
            'address': [
                r'address\s*[:\-=]\s*(.{10,80}?)(?=\s*(?:gender|phone|contact|mobile|dob|date|issue|valid|email|$))',
                r'residential\s+address\s*[:\-=]\s*(.{10,60}?)(?=\s*(?:gender|phone|contact|$))',
            ],
            'applicant_address': [
                r'(?:applicant\s+)?address\s*[:\-=]\s*(.{10,80}?)(?=\s*(?:gender|phone|contact|mobile|dob|date|issue|valid|$))',
                r'(\d+\s+[A-Za-z\s]+(?:nagar|colony|street|road|lane|avenue)\s*,\s*[A-Za-z\s,]+\d{6})',
            ],
            # ── Personal attributes ───────────────────────────────────────
            'gender': [
                r'gender\s*[:\-=]\s*(male|female|other|transgender)',
                r'\b(male|female)\b(?!\s*(?:ward|patient|doctor))',
            ],
            'nationality': [
                r'nationality\s*[:\-=]\s*([A-Za-z]+)',
                r'citizenship\s*[:\-=]\s*([A-Za-z]+)',
            ],
            'father_name': [
                r"father'?s?\s+name\s*[:\-=]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
                r's/o\.?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            ],
            'mother_name': [
                r"mother'?s?\s+name\s*[:\-=]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
                r'd/o\.?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            ],
            # ── Contact ──────────────────────────────────────────────────
            'contact_number': [
                r'(?:phone|contact|mobile|tel|mo?b?\.?)\s*(?:no|number)?\s*[:\-=]\s*([\+]?[\d\-\(\)\s]{10,})',
                r'\b(\+?91[\-\s]?\d{10})\b',
                r'\b(\d{10})\b',
            ],
            'email': [
                r'email\s*(?:id|address)?\s*[:\-=]\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})',
                r'\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b',
            ],
            # ── Document-specific ─────────────────────────────────────────
            'document_type_specific': [
                r'^([A-Z][A-Z\s]{3,}(?:CARD|CERTIFICATE|LICENCE|LICENSE|PERMIT|PASS))$',
                r'(?:type|category)\s*[:\-=]\s*([A-Za-z\s]+?)(?:\n|$)',
            ],
            'purpose': [
                r'purpose\s*[:\-=]\s*([^\n]+?)(?:\s+[A-Z][a-z]+\s*[:\-=]|$)',
                r'reason\s*[:\-=]\s*([^\n]+?)(?:\s+[A-Z][a-z]+\s*[:\-=]|$)',
            ],
            'department': [
                r'department\s*[:\-=]\s*([^\n]+?)(?:\s+[A-Z]|$)',
                r'dept\.?\s*[:\-=]\s*([^\n]+?)(?:\s+[A-Z]|$)',
            ],
            'document_title': [
                r'^([A-Z\s]{5,}(?:FORM|APPLICATION|CERTIFICATE|LICENSE|PERMIT|CARD))$',
            ],
            # ── CSR Document Fields ───────────────────────────────────────
            'project_title': [
                r'project\s+title\s*[:\-=]\s*([^\n\r]+)',
                r'project\s+name\s*[:\-=]\s*([^\n\r]+)',
                r'title\s+of\s+(?:the\s+)?project\s*[:\-=]\s*([^\n\r]+)',
            ],
            'implementing_agency': [
                r'implementing\s+(?:agency|organization|partner|ngo)\s*[:\-=]\s*([^\n\r]+)',
                r'agency\s+name\s*[:\-=]\s*([^\n\r]+)',
                r'executed\s+by\s*[:\-=]\s*([^\n\r]+)',
            ],
            'target_beneficiaries': [
                r'target\s+beneficiaries\s*[:\-=]\s*([^\n\r]+)',
                r'beneficiaries\s*[:\-=]\s*([^\n\r]+)',
            ],
            'total_budget': [
                r'total\s+budget\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'project\s+budget\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'budget\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
            ],
            'project_duration': [
                r'project\s+duration\s*[:\-=]\s*([^\n\r]+)',
                r'duration\s*[:\-=]\s*([^\n\r]+)',
                r'timeline\s*[:\-=]\s*([^\n\r]+)',
            ],
            'project_location': [
                r'project\s+location\s*[:\-=]\s*([^\n\r]+)',
                r'location\s*[:\-=]\s*([^\n\r]+)',
            ],
            'objectives': [
                r'objectives\s*[:\-=]\s*([^\n\r]+)',
                r'project\s+objectives\s*[:\-=]\s*([^\n\r]+)',
            ],
            'csr_schedule': [
                r'csr\s+schedule\s*[:\-=]\s*([^\n\r]+)',
                r'schedule\s+vii\s*(?:category)?\s*[:\-=]\s*([^\n\r]+)',
            ],
            'contact_person': [
                r'contact\s+person\s*[:\-=]\s*([^\n\r]+)',
                r'nodal\s+officer\s*[:\-=]\s*([^\n\r]+)',
            ],
            'submission_date': [
                r'submission\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'date\s+of\s+submission\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'submitted\s+on\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'financial_year': [
                r'financial\s+year\s*[:\-=]\s*([A-Z0-9\-\/]+)',
                r'\bfy\s*[:\-=]?\s*([0-9]{2,4}[\-\/][0-9]{2,4})\b',
            ],
            'allocated_budget': [
                r'allocated\s+budget\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'budget\s+allocated\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
            ],
            'spent_amount': [
                r'spent\s+amount\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'total\s+expenditure\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'amount\s+spent\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
            ],
            'unspent_amount': [
                r'unspent\s+amount\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'balance\s+amount\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
            ],
            'budget_categories': [
                r'budget\s+categories\s*[:\-=]\s*([^\n\r]+)',
                r'category\s+breakdown\s*[:\-=]\s*([^\n\r]+)',
            ],
            'reporting_period': [
                r'reporting\s+period\s*[:\-=]\s*([^\n\r]+)',
                r'report\s+period\s*[:\-=]\s*([^\n\r]+)',
                r'period\s*[:\-=]\s*([^\n\r]+)',
            ],
            'milestones_achieved': [
                r'milestones\s+achieved\s*[:\-=]\s*([^\n\r]+)',
                r'key\s+milestones\s*[:\-=]\s*([^\n\r]+)',
            ],
            'funds_utilized': [
                r'funds\s+utilized\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'utilized\s+amount\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
            ],
            'beneficiary_count': [
                r'beneficiary\s+count\s*[:\-=]\s*([\d,]+)',
                r'number\s+of\s+beneficiaries\s*[:\-=]\s*([\d,]+)',
            ],
            'challenges': [
                r'challenges\s*[:\-=]\s*([^\n\r]+)',
            ],
            'uc_number': [
                r'uc\s+(?:no|number|#)\s*[:\-=]\s*([A-Z0-9\-\/]+)',
                r'utilization\s+certificate\s+(?:no|number)\s*[:\-=]\s*([A-Z0-9\-\/]+)',
            ],
            'certified_amount': [
                r'certified\s+amount\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'amount\s+certified\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
            ],
            'utilization_percentage': [
                r'utilization\s+percentage\s*[:\-=]\s*([\d\.]+)%?',
                r'utilization\s+percent\s*[:\-=]\s*([\d\.]+)%?',
                r'percentage\s+utilized\s*[:\-=]\s*([\d\.]+)%?',
            ],
            'certification_date': [
                r'certification\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'date\s+of\s+certification\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'chartered_accountant_name': [
                r'chartered\s+accountant\s*(?:name)?\s*[:\-=]\s*([^\n\r]+)',
                r'ca\s+name\s*[:\-=]\s*([^\n\r]+)',
                r'audited\s+by\s+ca\s*[:\-=]\s*([^\n\r]+)',
            ],
            'completion_date': [
                r'completion\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'date\s+of\s+completion\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'completed\s+on\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'final_cost': [
                r'final\s+cost\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'total\s+final\s+cost\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
            ],
            'target_achieved': [
                r'target\s+achieved\s*[:\-=]\s*([^\n\r]+)',
                r'targets\s+achieved\s*[:\-=]\s*([^\n\r]+)',
            ],
            'impact_summary': [
                r'impact\s+summary\s*[:\-=]\s*([^\n\r]+)',
                r'overall\s+impact\s*[:\-=]\s*([^\n\r]+)',
            ],
            'company_name': [
                r'company\s+name\s*[:\-=]\s*([^\n\r]+)',
                r'corporate\s+name\s*[:\-=]\s*([^\n\r]+)',
                r'name\s+of\s+(?:the\s+)?company\s*[:\-=]\s*([^\n\r]+)',
            ],
            'compliance_status': [
                r'compliance\s+status\s*[:\-=]\s*([^\n\r]+)',
                r'status\s*[:\-=]\s*(compliant|non-compliant|pending)',
            ],
            'authorized_signatory': [
                r'authorized\s+signatory\s*[:\-=]\s*([^\n\r]+)',
                r'signatory\s*[:\-=]\s*([^\n\r]+)',
            ],
            'agreement_title': [
                r'agreement\s+title\s*[:\-=]\s*([^\n\r]+)',
                r'mou\s+title\s*[:\-=]\s*([^\n\r]+)',
            ],
            'partner_organization': [
                r'partner\s+organization\s*[:\-=]\s*([^\n\r]+)',
                r'partner\s+name\s*[:\-=]\s*([^\n\r]+)',
            ],
            'agreement_date': [
                r'agreement\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'execution\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'funding_amount': [
                r'funding\s+amount\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
                r'grant\s+amount\s*[:\-=]\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
            ],
            'validity_period': [
                r'validity\s+period\s*[:\-=]\s*([^\n\r]+)',
                r'tenure\s*[:\-=]\s*([^\n\r]+)',
            ],
            'audit_report_number': [
                r'audit\s+report\s+(?:no|number|#)\s*[:\-=]\s*([A-Z0-9\-\/]+)',
            ],
            'auditor_name': [
                r'auditor\s+name\s*[:\-=]\s*([^\n\r]+)',
                r'audited\s+by\s*[:\-=]\s*([^\n\r]+)',
            ],
            'audit_opinion': [
                r'audit\s+opinion\s*[:\-=]\s*([^\n\r]+)',
                r'opinion\s*[:\-=]\s*([^\n\r]+)',
            ],
            'audit_date': [
                r'audit\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'assessing_agency': [
                r'assessing\s+agency\s*[:\-=]\s*([^\n\r]+)',
                r'evaluation\s+agency\s*[:\-=]\s*([^\n\r]+)',
            ],
            'assessment_period': [
                r'assessment\s+period\s*[:\-=]\s*([^\n\r]+)',
            ],
            'impact_score': [
                r'impact\s+score\s*[:\-=]\s*([^\n\r]+)',
                r'rating\s*[:\-=]\s*([^\n\r]+)',
            ],
            'key_findings': [
                r'key\s+findings\s*[:\-=]\s*([^\n\r]+)',
                r'findings\s*[:\-=]\s*([^\n\r]+)',
            ],
            'assessment_date': [
                r'assessment\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'policy_version': [
                r'policy\s+version\s*[:\-=]\s*([^\n\r]+)',
                r'version\s*[:\-=]\s*([^\n\r]+)',
            ],
            'approval_date': [
                r'approval\s+date\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'approved\s+on\s*[:\-=]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'focus_areas': [
                r'focus\s+areas\s*[:\-=]\s*([^\n\r]+)',
                r'thrust\s+areas\s*[:\-=]\s*([^\n\r]+)',
            ],
            'csr_committee_members': [
                r'csr\s+committee\s+members\s*[:\-=]\s*([^\n\r]+)',
                r'committee\s+members\s*[:\-=]\s*([^\n\r]+)',
            ],
        }
        
        # Try patterns for this field
        patterns = field_patterns.get(field_name, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                # Clean up value
                value = re.sub(r'\s+', ' ', value)  # Normalize spaces
                value = value.rstrip(',.')  # Remove trailing punctuation
                value = value.strip()
                
                if value and len(value) > 1:  # Avoid single character matches
                    logger.info(f"Extracted {field_name}: {value}")
                    return value, 0.9
        
        # Not found
        logger.debug(f"Field {field_name} not found in text")
        return None, 0.0
    
    @staticmethod
    def _get_field_name(field: Any) -> str:
        """Extract field name from field definition."""
        if isinstance(field, dict):
            return field.get("name", str(field))
        return str(field)
    
    @staticmethod
    def _get_field_info(fields: List[Any], field_name: str) -> Dict[str, Any]:
        """Get field metadata from schema."""
        for field in fields:
            if isinstance(field, dict) and field.get("name") == field_name:
                return field
        return {}
    
    def _parse_llm_response(
        self, 
        raw_response: str, 
        fields: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse LLM response to extract field values and confidence.
        
        Args:
            raw_response: Raw LLM output
            fields: List of field definitions from schema
            
        Returns:
            List of parsed fields with value and confidence
        """
        # Try to find JSON in the response
        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if not match:
            logger.warning("No JSON found in LLM response")
            return [
                {
                    "field": self._get_field_name(f), 
                    "value": None, 
                    "confidence": 0.0
                } 
                for f in fields
            ]
        
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {e}")
            return [
                {
                    "field": self._get_field_name(f), 
                    "value": None, 
                    "confidence": 0.0
                } 
                for f in fields
            ]
        
        # Extract field values
        results = []
        for field in fields:
            field_name = self._get_field_name(field)
            field_data = parsed.get(field_name, {})
            
            # Handle both dict format and direct value
            if isinstance(field_data, dict):
                value = field_data.get("value")
                confidence = field_data.get("confidence", 0.0)
            else:
                value = field_data
                confidence = 0.7 if value is not None else 0.0
            
            results.append({
                "field": field_name,
                "value": value,
                "confidence": float(confidence) if confidence is not None else 0.0
            })
        
        return results
