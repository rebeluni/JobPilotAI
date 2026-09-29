"""
India Domestic Work Authorization Evaluator for JobPilot AI.
Evaluates domestic rights for Indian citizens (no visa/sponsorship needed).
"""

from typing import Any, Dict, Optional
from jobpilot.core.schemas import ConfidenceLevel, JobRecord, VisaEvidence, VisaStatus
from jobpilot.immigration.evidence import extract_evidence_snippets, build_visa_evidence


def evaluate_india(job: JobRecord, rule: Optional[Dict[str, Any]] = None) -> VisaEvidence:
    """
    Evaluates immigration/work authorization for roles based in India.
    Indian citizens have full domestic work authorization without sponsorship.
    """
    snippets = extract_evidence_snippets(job.description)
    default_snippets = ["Indian citizen domestic authorization", "No visa sponsorship required for roles in India"]
    all_snippets = default_snippets + [s for s in snippets if s not in default_snippets]

    rule = rule or {}
    route_name = rule.get("route", "Citizen / Domestic Authorization")
    notes = rule.get("notes", "Authorized to work in India without sponsorship.")

    return build_visa_evidence(
        country="India",
        visa_status=VisaStatus.INDIA,
        route=route_name,
        confidence=ConfidenceLevel.HIGH,
        threshold_met=True,
        threshold_details={
            "domestic_authorization": True,
            "requires_sponsorship": False,
            "notes": notes,
        },
        sponsor_status="Domestic (No sponsorship required)",
        evidence_snippets=all_snippets,
        verified_rule=True,
    )
