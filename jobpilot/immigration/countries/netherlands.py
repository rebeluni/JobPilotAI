"""
Netherlands Highly Skilled Migrant (Kennismigrant) Evaluator for JobPilot AI.
Checks IND recognized sponsor status and monthly gross salary thresholds.
"""

from typing import Any, Dict, Optional
from jobpilot.core.schemas import JobRecord, VisaEvidence
from jobpilot.immigration.countries.base import evaluate_foreign_country


def evaluate_netherlands(job: JobRecord, rule: Optional[Dict[str, Any]] = None) -> VisaEvidence:
    """Evaluates Netherlands Highly Skilled Migrant suitability."""
    return evaluate_foreign_country(
        job=job,
        country_name="Netherlands",
        default_route="Highly Skilled Migrant (Kennismigrant)",
        salary_key="min_salary_eur",
        rule=rule,
        additional_notes="Employer must be recognized sponsor registered with the IND.",
    )
