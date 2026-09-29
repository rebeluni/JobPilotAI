"""
Country-Specific Immigration Evaluators for JobPilot AI.
Exports evaluators for India, UK, Germany, Netherlands, Canada, Australia, Singapore, and UAE.
"""

from typing import Any, Callable, Dict, Optional
from jobpilot.core.schemas import JobRecord, VisaEvidence
from jobpilot.immigration.countries.india import evaluate_india
from jobpilot.immigration.countries.uk import evaluate_uk
from jobpilot.immigration.countries.germany import evaluate_germany
from jobpilot.immigration.countries.netherlands import evaluate_netherlands
from jobpilot.immigration.countries.canada import evaluate_canada
from jobpilot.immigration.countries.australia import evaluate_australia
from jobpilot.immigration.countries.singapore import evaluate_singapore
from jobpilot.immigration.countries.uae import evaluate_uae
from jobpilot.immigration.countries.base import evaluate_foreign_country

COUNTRY_EVALUATORS: Dict[str, Callable[[JobRecord, Optional[Dict[str, Any]]], VisaEvidence]] = {
    "india": evaluate_india,
    "in": evaluate_india,
    "uk": evaluate_uk,
    "united kingdom": evaluate_uk,
    "great britain": evaluate_uk,
    "england": evaluate_uk,
    "germany": evaluate_germany,
    "de": evaluate_germany,
    "deutschland": evaluate_germany,
    "netherlands": evaluate_netherlands,
    "nl": evaluate_netherlands,
    "holland": evaluate_netherlands,
    "canada": evaluate_canada,
    "ca": evaluate_canada,
    "australia": evaluate_australia,
    "au": evaluate_australia,
    "singapore": evaluate_singapore,
    "sg": evaluate_singapore,
    "uae": evaluate_uae,
    "united arab emirates": evaluate_uae,
    "dubai": evaluate_uae,
}


def get_country_evaluator(country: Optional[str]) -> Callable[[JobRecord, Optional[Dict[str, Any]]], VisaEvidence]:
    """
    Returns the appropriate country evaluator function based on country name or alias.
    Falls back to a generic foreign evaluator if country is not in the explicit list.
    """
    if not country:
        # Default to India if not specified, or fallback to generic
        return evaluate_india

    norm = country.strip().lower()
    if norm in COUNTRY_EVALUATORS:
        return COUNTRY_EVALUATORS[norm]

    # Fallback generic evaluator
    def generic_evaluator(job: JobRecord, rule: Optional[Dict[str, Any]] = None) -> VisaEvidence:
        return evaluate_foreign_country(
            job=job,
            country_name=country,
            default_route="Skilled Worker / Work Permit",
            rule=rule,
        )

    return generic_evaluator
