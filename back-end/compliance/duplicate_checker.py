"""
CSR Duplicate & Double-Funding Detection Engine.

Performs exact hash matching, fuzzy text similarity scanning, and
double-funding claim detection across CSR documents and projects.
"""

import hashlib
import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Try rapidfuzz, fallback to token-based ratio
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not installed; using token-overlap similarity fallback")


def calculate_text_hash(text: str) -> str:
    """Generate normalized SHA-256 hash of text content."""
    if not text:
        return ""
    normalized = re.sub(r'\s+', ' ', text.strip().lower())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def calculate_fuzzy_similarity(text1: str, text2: str) -> float:
    """Calculate string similarity ratio (0.0 to 1.0)."""
    if not text1 or not text2:
        return 0.0
    t1 = text1.strip().lower()[:2000]
    t2 = text2.strip().lower()[:2000]
    if t1 == t2:
        return 1.0

    if RAPIDFUZZ_AVAILABLE:
        return fuzz.token_sort_ratio(t1, t2) / 100.0
    else:
        # Token overlap fallback
        words1 = set(re.findall(r'\w+', t1))
        words2 = set(re.findall(r'\w+', t2))
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)


class DuplicateChecker:
    """
    Intelligent Duplicate & Double-Funding Detector.
    """

    @staticmethod
    def check_exact_duplicate(
        raw_text: str,
        doc_registry: Dict[str, Dict[str, Any]],
        exclude_doc_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if raw_text exactly matches an existing document by hash."""
        target_hash = calculate_text_hash(raw_text)
        if not target_hash:
            return False, None

        for doc_id, doc in doc_registry.items():
            if exclude_doc_id and doc_id == exclude_doc_id:
                continue
            existing_hash = doc.get("text_hash") or calculate_text_hash(doc.get("raw_text_preview", ""))
            if existing_hash and existing_hash == target_hash:
                logger.warning(f"Exact duplicate detected with document '{doc_id}'")
                return True, doc

        return False, None

    @staticmethod
    def check_fuzzy_duplicate(
        raw_text: str,
        doc_registry: Dict[str, Dict[str, Any]],
        threshold: float = 0.85,
        exclude_doc_id: Optional[str] = None,
    ) -> Tuple[bool, float, Optional[Dict[str, Any]]]:
        """Scan registry for fuzzy text similarity above threshold."""
        if not raw_text or not raw_text.strip():
            return False, 0.0, None

        best_score = 0.0
        matched_doc = None

        for doc_id, doc in doc_registry.items():
            if exclude_doc_id and doc_id == exclude_doc_id:
                continue
            existing_text = doc.get("raw_text_preview", "")
            if not existing_text:
                continue

            sim = calculate_fuzzy_similarity(raw_text, existing_text)
            if sim > best_score:
                best_score = sim
                matched_doc = doc

        if best_score >= threshold:
            logger.warning(f"Fuzzy duplicate detected (score={best_score:.2f}) with document '{matched_doc.get('document_id')}'")
            return True, best_score, matched_doc

        return False, best_score, matched_doc

    @staticmethod
    def check_double_funding_claim(
        extracted_fields: List[Dict[str, Any]],
        doc_registry: Dict[str, Dict[str, Any]],
        exclude_doc_id: Optional[str] = None,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Scan extracted fields for double-funding markers:
        - Duplicate UC Number (utilization certificate)
        - Duplicate Audit Report Number
        - Duplicate Project Title + Total Budget combination
        """
        duplicates_found = []
        if not extracted_fields:
            return False, []

        # Convert extracted_fields list to dict
        field_dict = {}
        for f in extracted_fields:
            if isinstance(f, dict):
                field_dict[f.get("field", "")] = str(f.get("value", "")).strip()

        uc_no = field_dict.get("uc_number") or field_dict.get("certificate_number")
        audit_no = field_dict.get("audit_report_number") or field_dict.get("report_number")
        title = field_dict.get("project_title")
        budget = field_dict.get("total_budget")

        for doc_id, doc in doc_registry.items():
            if exclude_doc_id and doc_id == exclude_doc_id:
                continue

            ex_fields = doc.get("extracted_fields", [])
            other_dict = {}
            for ef in ex_fields:
                if isinstance(ef, dict):
                    other_dict[ef.get("field", "")] = str(ef.get("value", "")).strip()

            other_uc = other_dict.get("uc_number") or other_dict.get("certificate_number")
            other_audit = other_dict.get("audit_report_number") or other_dict.get("report_number")
            other_title = other_dict.get("project_title")
            other_budget = other_dict.get("total_budget")

            # 1. Match UC Number
            if uc_no and other_uc and uc_no.lower() == other_uc.lower():
                duplicates_found.append({
                    "reason": "DUPLICATE_UC_NUMBER",
                    "matched_field": "uc_number",
                    "value": uc_no,
                    "matched_document_id": doc_id,
                    "filename": doc.get("filename"),
                })

            # 2. Match Audit Report Number
            if audit_no and other_audit and audit_no.lower() == other_audit.lower():
                duplicates_found.append({
                    "reason": "DUPLICATE_AUDIT_NUMBER",
                    "matched_field": "audit_report_number",
                    "value": audit_no,
                    "matched_document_id": doc_id,
                    "filename": doc.get("filename"),
                })

            # 3. Match Title + Budget
            if title and budget and other_title and other_budget:
                if (title.lower() == other_title.lower()) and (budget == other_budget):
                    duplicates_found.append({
                        "reason": "DOUBLE_FUNDING_CLAIM",
                        "matched_field": "project_title_and_budget",
                        "value": f"{title} (Rs {budget})",
                        "matched_document_id": doc_id,
                        "filename": doc.get("filename"),
                    })

        is_duplicate = len(duplicates_found) > 0
        return is_duplicate, duplicates_found
