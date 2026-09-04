"""
CSR Statutory Compliance Verifier.

Enforces Companies Act Section 135 statutory compliance, 2% net profit budget calculations,
Schedule VII activity alignment, CA FRN verification, and Form CSR-1 credentials validation.
"""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Permissible Schedule VII Focus Categories
SCHEDULE_VII_CATEGORIES = {
    "HUNGER_HEALTH_WATER": {
        "title": "Item (i): Eradicating hunger, poverty, health care & safe drinking water",
        "keywords": ["hunger", "poverty", "malnutrition", "healthcare", "health", "drinking water", "sanitation", "swachh bharat"]
    },
    "EDUCATION_SKILLS": {
        "title": "Item (ii): Promoting education, vocational skills & livelihood enhancement",
        "keywords": ["education", "school", "literacy", "vocational", "skill development", "livelihood", "special education"]
    },
    "GENDER_EQUALITY": {
        "title": "Item (iii): Gender equality, women empowerment & senior citizen welfare",
        "keywords": ["gender equality", "women empowerment", "girl child", "day care", "senior citizens", "hostel"]
    },
    "ENVIRONMENT_SUSTAINABILITY": {
        "title": "Item (iv): Environmental sustainability, flora/fauna & animal welfare",
        "keywords": ["environment", "sustainability", "solar", "renewable", "plantation", "tree", "ecological", "animal welfare", "water conservation"]
    },
    "HERITAGE_CULTURE": {
        "title": "Item (v): National heritage, art, culture & public libraries",
        "keywords": ["heritage", "art", "culture", "monuments", "public library", "crafts"]
    },
    "ARMED_FORCES": {
        "title": "Item (vi): Armed forces veterans, war widows & dependents",
        "keywords": ["armed forces", "veterans", "war widows", "ex-servicemen"]
    },
    "SPORTS": {
        "title": "Item (vii): Rural & national sports training",
        "keywords": ["sports", "rural sports", "paralympic", "olympic", "athletes"]
    },
    "RELIEF_FUNDS": {
        "title": "Item (viii): PM National Relief Fund, PM CARES & socioeconomic funds",
        "keywords": ["pm cares", "national relief fund", "pm nrf", "socioeconomic development"]
    },
    "RURAL_SLUM_DEVELOPMENT": {
        "title": "Item (x): Slum area & rural development projects",
        "keywords": ["rural development", "village", "slum development", "rural infrastructure", "panchayat"]
    },
    "DISASTER_MANAGEMENT": {
        "title": "Item (xii): Disaster management, relief & rehabilitation",
        "keywords": ["disaster management", "disaster relief", "flood relief", "earthquake", "rehabilitation", "cyclone"]
    }
}


def verify_section_135_eligibility(
    average_net_profit: float,
    allocated_csr_budget: float,
    net_worth: float = 0.0,
    turnover: float = 0.0,
) -> Dict[str, Any]:
    """
    Validate Section 135 Companies Act eligibility & 2% average net profit budget rule.
    """
    is_eligible = (
        net_worth >= 5000000000.0 or
        turnover >= 10000000000.0 or
        average_net_profit >= 50000000.0
    )

    required_min_csr_budget = round(max(0.0, average_net_profit * 0.02), 2)
    meets_2_percent = allocated_csr_budget >= required_min_csr_budget

    shortfall = max(0.0, required_min_csr_budget - allocated_csr_budget)
    utilization_rate = round((allocated_csr_budget / required_min_csr_budget * 100.0), 2) if required_min_csr_budget > 0 else 100.0

    return {
        "is_section_135_eligible": is_eligible,
        "average_net_profit": average_net_profit,
        "required_min_csr_budget_2_percent": required_min_csr_budget,
        "allocated_csr_budget": allocated_csr_budget,
        "meets_2_percent_rule": meets_2_percent,
        "shortfall_amount": shortfall,
        "csr_allocation_rate": min(100.0, utilization_rate),
    }


def verify_schedule_vii_alignment(text_or_objectives: str) -> Dict[str, Any]:
    """
    Check project objectives alignment with permissible Schedule VII categories.
    """
    if not text_or_objectives:
        return {
            "is_aligned": False,
            "matched_categories": [],
            "primary_category": None,
            "confidence": 0.0,
        }

    text_lower = text_or_objectives.lower()
    matched = []

    for cat_key, cat_info in SCHEDULE_VII_CATEGORIES.items():
        score = sum(1 for kw in cat_info["keywords"] if kw.lower() in text_lower)
        if score > 0:
            matched.append({
                "category_key": cat_key,
                "title": cat_info["title"],
                "keyword_matches": score,
            })

    matched.sort(key=lambda x: x["keyword_matches"], reverse=True)
    is_aligned = len(matched) > 0
    primary = matched[0]["title"] if matched else None
    confidence = min(0.95, 0.5 + len(matched) * 0.15) if is_aligned else 0.0

    return {
        "is_aligned": is_aligned,
        "matched_categories": matched,
        "primary_category": primary,
        "confidence": confidence,
    }


def verify_ca_and_csr1_credentials(
    ca_frn: Optional[str] = None,
    ca_membership: Optional[str] = None,
    csr1_number: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate formats for CA FRN, CA Membership, and Form CSR-1 Registration Numbers.
    """
    frn_valid = bool(re.match(r'^\d{6}[A-Z]$', ca_frn.strip().upper())) if ca_frn else None
    mem_valid = bool(re.match(r'^\d{5,6}$', ca_membership.strip())) if ca_membership else None
    csr1_valid = bool(re.match(r'^CSR\d{8,9}$', csr1_number.strip().upper())) if csr1_number else None

    return {
        "ca_frn_valid": frn_valid,
        "ca_membership_valid": mem_valid,
        "csr1_registration_valid": csr1_valid,
        "all_credentials_valid": all(v is not False for v in (frn_valid, mem_valid, csr1_valid)),
    }


class StatutoryComplianceVerifier:
    """
    Comprehensive CSR Statutory Compliance & Governance Auditor.
    """

    @staticmethod
    def generate_compliance_report(
        project_title: str,
        objectives: str,
        allocated_csr_budget: float,
        average_net_profit: float = 0.0,
        ca_frn: Optional[str] = None,
        csr1_number: Optional[str] = None,
        duplicate_flagged: bool = False,
    ) -> Dict[str, Any]:
        """Generate comprehensive CSR Compliance & Risk Report."""
        checks = []
        total_score = 100.0

        # Check 1: Schedule VII Alignment
        sch7_res = verify_schedule_vii_alignment(objectives or project_title)
        if sch7_res["is_aligned"]:
            checks.append({
                "rule": "SCHEDULE_VII_ALIGNMENT",
                "status": "PASS",
                "score_impact": 0,
                "message": f"Project aligns with {sch7_res['primary_category']}",
            })
        else:
            total_score -= 30.0
            checks.append({
                "rule": "SCHEDULE_VII_ALIGNMENT",
                "status": "FAIL",
                "score_impact": -30,
                "message": "Project objectives do not match standard Schedule VII CSR focus categories",
            })

        # Check 2: Section 135 2% Net Profit Rule
        if average_net_profit > 0:
            sec135_res = verify_section_135_eligibility(average_net_profit, allocated_csr_budget)
            if sec135_res["meets_2_percent_rule"]:
                checks.append({
                    "rule": "SECTION_135_2_PERCENT_RULE",
                    "status": "PASS",
                    "score_impact": 0,
                    "message": f"Allocated CSR budget (Rs {allocated_csr_budget}) meets mandatory 2% average net profit threshold (Rs {sec135_res['required_min_csr_budget_2_percent']})",
                })
            else:
                total_score -= 25.0
                checks.append({
                    "rule": "SECTION_135_2_PERCENT_RULE",
                    "status": "FAIL",
                    "score_impact": -25,
                    "message": f"Allocated CSR budget has a shortfall of Rs {sec135_res['shortfall_amount']} relative to 2% requirement",
                })

        # Check 3: CA FRN & Form CSR-1 credentials
        cred_res = verify_ca_and_csr1_credentials(ca_frn=ca_frn, csr1_number=csr1_number)
        if cred_res["all_credentials_valid"]:
            checks.append({
                "rule": "CREDENTIALS_FORMAT_CHECK",
                "status": "PASS",
                "score_impact": 0,
                "message": "CA FRN and Form CSR-1 credentials are format compliant",
            })
        else:
            total_score -= 15.0
            checks.append({
                "rule": "CREDENTIALS_FORMAT_CHECK",
                "status": "WARNING",
                "score_impact": -15,
                "message": "One or more statutory credentials (CA FRN or Form CSR-1) are missing or invalid",
            })

        # Check 4: Duplicate Flag Check
        if duplicate_flagged:
            total_score -= 40.0
            checks.append({
                "rule": "DUPLICATE_DOUBLE_FUNDING_CHECK",
                "status": "FAIL",
                "score_impact": -40,
                "message": "Flagged for potential duplicate document upload or double-funding claim",
            })
        else:
            checks.append({
                "rule": "DUPLICATE_DOUBLE_FUNDING_CHECK",
                "status": "PASS",
                "score_impact": 0,
                "message": "No duplicate documents or double-funding claims detected",
            })

        final_score = max(0.0, round(total_score, 2))

        # Overall Status & Risk Determination
        if duplicate_flagged:
            status = "FLAGGED_DUPLICATE"
            risk_level = "CRITICAL"
        elif final_score >= 85.0:
            status = "FULLY_COMPLIANT"
            risk_level = "LOW"
        elif final_score >= 60.0:
            status = "PARTIALLY_COMPLIANT"
            risk_level = "MEDIUM"
        else:
            status = "NON_COMPLIANT"
            risk_level = "HIGH"

        return {
            "compliance_score": final_score,
            "status": status,
            "risk_level": risk_level,
            "schedule_vii": sch7_res,
            "checks": checks,
        }
