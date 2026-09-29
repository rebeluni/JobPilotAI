"""
UAE Green Visa and Employment Visa Evaluator for JobPilot AI.
Checks skilled worker classification and sponsorship criteria.
"""

from typing import Any, Dict, Optional
from jobpilot.core.schemas import JobRecord, VisaEvidence
from jobpilot.immigration.countries.base import evaluate_foreign_country


def evaluate_uae(job: JobRecord, rule: Optional[Dict[str, Any]] = None) -> VisaEvidence:
    """Evaluates UAE Green Visa and Standard Employment Visa suitability."""
    return evaluate_foreign_country(
        job=job,
        country_name="UAE",
        default_route="Green Visa / Standard Employment Visa",
        salary_key="min_salary_aed",
        rule=rule,
        additional_notes="Standard employer sponsorship or self-sponsored 5-year Green Visa for skilled professionals.",
    )
