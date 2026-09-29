"""
Germany EU Blue Card and Opportunity Card Evaluator for JobPilot AI.
Checks shortage occupation salary thresholds and recognized academic degree requirements.
"""

from typing import Any, Dict, Optional
from jobpilot.core.schemas import JobRecord, VisaEvidence
from jobpilot.immigration.countries.base import evaluate_foreign_country


def evaluate_germany(job: JobRecord, rule: Optional[Dict[str, Any]] = None) -> VisaEvidence:
    """Evaluates Germany EU Blue Card and Opportunity Card suitability."""
    return evaluate_foreign_country(
        job=job,
        country_name="Germany",
        default_route="EU Blue Card (§ 18g AufenthG) / Opportunity Card",
        salary_key="min_salary_eur",
        rule=rule,
        additional_notes="Requires recognized university degree and employment contract with eligible salary.",
    )
