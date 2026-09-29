"""
Australia Skills in Demand Visa (Subclass 482) Evaluator for JobPilot AI.
Checks TSMIT salary threshold and skilled occupation eligibility.
"""

from typing import Any, Dict, Optional
from jobpilot.core.schemas import JobRecord, VisaEvidence
from jobpilot.immigration.countries.base import evaluate_foreign_country


def evaluate_australia(job: JobRecord, rule: Optional[Dict[str, Any]] = None) -> VisaEvidence:
    """Evaluates Australia Skills in Demand / Subclass 482 suitability."""
    return evaluate_foreign_country(
        job=job,
        country_name="Australia",
        default_route="Skills in Demand Visa (Subclass 482 / TSS replacement)",
        salary_key="min_salary_aud",
        rule=rule,
        additional_notes="Requires approved employer sponsor and nomination on eligible skilled occupation list.",
    )
