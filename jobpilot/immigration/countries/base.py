"""
Base Evaluator for Foreign Country Immigration Viability.
Provides standardized threshold comparison, signal scanning, and confidence capping.
"""

from typing import Any, Dict, List, Optional
from jobpilot.core.schemas import ConfidenceLevel, JobRecord, VisaEvidence, VisaStatus
from jobpilot.immigration.evidence import (
    build_visa_evidence,
    extract_evidence_snippets,
    scan_sponsor_signals,
)


def evaluate_foreign_country(
    job: JobRecord,
    country_name: str,
    default_route: str,
    salary_key: Optional[str] = None,
    rule: Optional[Dict[str, Any]] = None,
    additional_notes: Optional[str] = None,
) -> VisaEvidence:
    """
    Evaluates foreign work visa viability for a job posting.
    Checks positive/negative sponsorship signals, salary thresholds (if verified),
    and strictly enforces confidence capping when rules are unverified.
    """
    rule = rule or {}
    route = rule.get("route", default_route)
    verified_rule = bool(rule.get("verified", False))
    requires_sponsorship = rule.get("requires_sponsorship", True)

    pos_signals, neg_signals = scan_sponsor_signals(job.description)
    snippets = extract_evidence_snippets(job.description)

    # Check salary threshold if configured
    threshold_met: Optional[bool] = None
    threshold_val = rule.get(salary_key) if salary_key else None
    threshold_details: Dict[str, Any] = {
        "requires_sponsorship": requires_sponsorship,
        "rule_threshold": threshold_val,
        "verified_rule": verified_rule,
        "source_url": rule.get("source_url"),
        "notes": rule.get("notes", additional_notes),
    }

    if isinstance(threshold_val, (int, float)):
        job_salary = job.salary_max or job.salary_min
        if job_salary is not None:
            threshold_met = bool(job_salary >= threshold_val)
            threshold_details["job_salary"] = job_salary
            threshold_details["threshold_met"] = threshold_met
    else:
        threshold_details["threshold_status"] = "NEEDS_VERIFICATION"

    # Determine Visa Status
    if neg_signals or (job.work_authorization_requirement and "citizen" in job.work_authorization_requirement.lower()):
        # Explicit exclusion or restriction
        if any("no " in s.lower() or "cannot" in s.lower() or "not available" in s.lower() for s in neg_signals):
            visa_status = VisaStatus.NOT_SUITABLE
            sponsor_status = "Sponsorship explicitly unavailable"
        else:
            visa_status = VisaStatus.SPONSORSHIP_UNLIKELY
            sponsor_status = "Sponsorship unlikely based on posting requirements"
        confidence = ConfidenceLevel.HIGH if verified_rule else ConfidenceLevel.LOW

    elif pos_signals or job.sponsor_verified or job.relocation_support:
        visa_status = VisaStatus.SPONSORSHIP_LIKELY
        sponsor_status = "Sponsorship / Relocation offered or verified"
        confidence = ConfidenceLevel.HIGH if verified_rule else ConfidenceLevel.LOW

    else:
        # No explicit signal in text
        # If it's a skilled technical / engineering / AI role
        tech_indicators = ["engineer", "developer", "scientist", "analyst", "ai", "machine learning", "data"]
        title_lower = (job.title or "").lower()
        is_tech_role = any(t in title_lower for t in tech_indicators)

        if is_tech_role:
            visa_status = VisaStatus.SPONSORSHIP_POSSIBLE
            sponsor_status = "Role may qualify for skilled worker visa; sponsorship unconfirmed"
            confidence = ConfidenceLevel.MEDIUM if verified_rule else ConfidenceLevel.LOW
        else:
            visa_status = VisaStatus.UNCLEAR
            sponsor_status = "Insufficient sponsorship information in job posting"
            confidence = ConfidenceLevel.LOW

    # Build evidence snippets
    evidence_items: List[str] = []
    if pos_signals:
        evidence_items.extend([f"Positive signal: {s}" for s in pos_signals])
    if neg_signals:
        evidence_items.extend([f"Negative signal: {s}" for s in neg_signals])
    if job.sponsor_verified:
        evidence_items.append("Employer verified in sponsor database")
    if job.relocation_support:
        evidence_items.append("Relocation support indicated in listing")
    evidence_items.extend([s for s in snippets if s not in evidence_items])

    return build_visa_evidence(
        country=country_name,
        visa_status=visa_status,
        route=route,
        confidence=confidence,
        threshold_met=threshold_met,
        threshold_details=threshold_details,
        sponsor_status=sponsor_status,
        evidence_snippets=evidence_items,
        verified_rule=verified_rule,
    )
