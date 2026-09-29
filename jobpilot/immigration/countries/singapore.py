"""
Singapore Employment Pass (EP) and COMPASS Evaluator for JobPilot AI.
Checks MOM qualifying salary benchmarks and points criteria.
"""

from typing import Any, Dict, Optional
from jobpilot.core.schemas import JobRecord, VisaEvidence
from jobpilot.immigration.countries.base import evaluate_foreign_country


def evaluate_singapore(job: JobRecord, rule: Optional[Dict[str, Any]] = None) -> VisaEvidence:
    """Evaluates Singapore Employment Pass (EP) suitability."""
    return evaluate_foreign_country(
        job=job,
        country_name="Singapore",
        default_route="Employment Pass (EP) / COMPASS Points",
        salary_key="min_salary_sgd",
        rule=rule,
        additional_notes="Subject to COMPASS framework scoring and MOM qualifying salary benchmarks.",
    )
