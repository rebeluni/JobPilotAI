"""
Canada Global Skills Strategy and Express Entry Evaluator for JobPilot AI.
Checks Global Talent Stream LMIA eligibility and job offer requirements.
"""

from typing import Any, Dict, Optional
from jobpilot.core.schemas import JobRecord, VisaEvidence
from jobpilot.immigration.countries.base import evaluate_foreign_country


def evaluate_canada(job: JobRecord, rule: Optional[Dict[str, Any]] = None) -> VisaEvidence:
    """Evaluates Canada Global Skills Strategy / Express Entry suitability."""
    return evaluate_foreign_country(
        job=job,
        country_name="Canada",
        default_route="Global Skills Strategy (GSS) / Express Entry LMIA",
        salary_key="min_salary_cad",
        rule=rule,
        additional_notes="Global Talent Stream allows expedited 2-week processing for qualifying tech roles.",
    )
