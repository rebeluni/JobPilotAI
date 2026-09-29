"""
Immigration Viability Classifier Pipeline Stage for JobPilot AI.
Evaluates work authorization and visa sponsorship eligibility for job postings,
integrating country-specific rules and mandatory legal disclaimers.
"""

from typing import Any, Dict, List, Optional, Union
from jobpilot.core.pipeline import PipelineStage
from jobpilot.core.schemas import ConfidenceLevel, JobRecord, VisaEvidence, VisaStatus
from jobpilot.immigration.countries import get_country_evaluator
from jobpilot.immigration.routes import RouteManager


class ImmigrationClassifier(PipelineStage):
    """
    Modular pipeline stage for evaluating immigration and visa sponsorship viability.
    Enforces that unverified rules cap confidence at LOW and always includes legal disclaimer.
    """
    stage_name = "immigration_classifier"

    def __init__(self, rules_path: Optional[str] = None):
        self.route_manager = RouteManager(rules_path=rules_path)

    def _infer_country_from_location(self, location: Optional[str]) -> Optional[str]:
        """Simple heuristic to infer country if country field is missing."""
        if not location:
            return None
        loc_lower = location.lower()
        if any(c in loc_lower for c in ["india", "mumbai", "bengaluru", "bangalore", "hyderabad", "delhi", "pune"]):
            return "India"
        if any(c in loc_lower for c in ["uk", "united kingdom", "london", "manchester", "birmingham"]):
            return "UK"
        if any(c in loc_lower for c in ["germany", "berlin", "munich", "frankfurt", "hamburg"]):
            return "Germany"
        if any(c in loc_lower for c in ["netherlands", "amsterdam", "rotterdam", "utrecht"]):
            return "Netherlands"
        if any(c in loc_lower for c in ["canada", "toronto", "vancouver", "montreal", "ottawa"]):
            return "Canada"
        if any(c in loc_lower for c in ["australia", "sydney", "melbourne", "brisbane"]):
            return "Australia"
        if any(c in loc_lower for c in ["singapore"]):
            return "Singapore"
        if any(c in loc_lower for c in ["uae", "dubai", "abu dhabi"]):
            return "UAE"
        return None

    def classify(self, job: JobRecord) -> VisaEvidence:
        """
        Evaluates a single JobRecord and updates its immigration fields in-place.
        Returns the resulting VisaEvidence.
        """
        country = job.country
        if not country or country.lower() in ("unknown", "remote"):
            # Check location if country not explicitly set
            inferred = self._infer_country_from_location(job.location)
            if inferred:
                country = inferred

        evaluator = get_country_evaluator(country)
        rule = self.route_manager.get_country_rule(country)

        evidence = evaluator(job, rule)

        # Update JobRecord contract fields
        job.visa_status = evidence.visa_status
        job.visa_evidence = evidence.model_dump()
        job.immigration_route = evidence.route
        if evidence.sponsor_status and "verified" in evidence.sponsor_status.lower():
            job.sponsor_verified = True

        return evidence

    def classify_all(self, jobs: List[JobRecord]) -> List[JobRecord]:
        """Classifies a list of jobs, updating each in-place."""
        for job in jobs:
            self.classify(job)
        return jobs

    async def run(self, input_data: Union[JobRecord, List[JobRecord]]) -> Union[JobRecord, List[JobRecord]]:
        """Pipeline stage entrypoint."""
        if isinstance(input_data, list):
            return self.classify_all(input_data)
        elif isinstance(input_data, JobRecord):
            self.classify(input_data)
            return input_data
        else:
            raise ValueError(f"ImmigrationClassifier expected JobRecord or List[JobRecord], got {type(input_data)}")

    async def health_check(self) -> bool:
        """Verifies rules configuration exists and is readable."""
        rules = self.route_manager.load_rules()
        return len(rules) > 0
