"""
UK Skilled Worker Visa Evaluator for JobPilot AI.
Checks sponsor license signals, salary thresholds, and shortage/eligible occupations.
"""

from typing import Any, Dict, Optional
from jobpilot.core.schemas import JobRecord, VisaEvidence
from jobpilot.immigration.countries.base import evaluate_foreign_country


def evaluate_uk(job: JobRecord, rule: Optional[Dict[str, Any]] = None) -> VisaEvidence:
    """Evaluates UK Skilled Worker Visa suitability."""
    return evaluate_foreign_country(
        job=job,
        country_name="UK",
        default_route="Skilled Worker Visa",
        salary_key="min_salary_gbp",
        rule=rule,
        additional_notes="Requires licensed sponsor, valid Certificate of Sponsorship (CoS), and salary meeting threshold.",
    )
