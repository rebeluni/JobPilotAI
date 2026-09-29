"""
Job Quality and Freshness Checker for JobPilot AI.
Detects expired postings, ghost jobs, scam signals, and incomplete postings.
Computes a comprehensive quality_score (0.0 to 1.0) and assigns audit flags.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import re

from jobpilot.core.pipeline import PipelineStage
from jobpilot.core.schemas import JobRecord


EXPIRED_PATTERNS = [
    r"position (?:has been )?filled",
    r"job (?:is )?no longer available",
    r"this job has expired",
    r"no longer accepting applications",
    r"application (?:is )?closed",
    r"this listing has expired",
    r"posting has closed",
]

SCAM_PATTERNS = [
    r"wire transfer",
    r"western union",
    r"money gram",
    r"cashier'?s check",
    r"pay (?:an? )?application fee",
    r"processing fee of",
    r"crypto(?:currency)? transfer",
    r"send money before starting",
    r"telegram interview",
    r"whatsapp interview only",
]


class JobQualityChecker(PipelineStage):
    """Evaluates posting freshness, legitimacy, and completeness."""

    stage_name: str = "quality_checker"

    def assess_quality(self, job: JobRecord, existing_postings: Optional[List[JobRecord]] = None) -> JobRecord:
        """
        Evaluate JobRecord quality, update flags, and return modified record.
        """
        score = 1.0
        desc = job.description or ""
        desc_lower = desc.lower()
        title_lower = job.title.lower()
        combined = f"{title_lower} {desc_lower}"

        # 1. Expired check: explicit keywords in description
        for pattern in EXPIRED_PATTERNS:
            if re.search(pattern, combined):
                job.is_expired = True
                score -= 0.50
                break

        # 2. Expired check: date_posted age (> 60 days)
        if job.date_posted:
            try:
                posted_dt = datetime.fromisoformat(job.date_posted.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if (now - posted_dt) > timedelta(days=60):
                    job.is_expired = True
                    score -= 0.35
            except Exception:
                pass

        # 3. Scam signals check
        for pattern in SCAM_PATTERNS:
            if re.search(pattern, combined):
                score -= 0.70
                break

        # Unrealistic compensation heuristic (e.g. > $400k for junior or non-executive role)
        if job.currency == "USD" and job.salary_min and job.salary_min > 400000:
            if "director" not in title_lower and "vp" not in title_lower and "chief" not in title_lower:
                score -= 0.30

        # Suspicious free email domain in job description
        if re.search(r"@(?:gmail|yahoo|hotmail|outlook)\.com", desc_lower):
            score -= 0.25

        # 4. Ghost job check: same company & title posted months ago without hiring
        if existing_postings:
            same_company_title = [
                p for p in existing_postings
                if p.company.lower() == job.company.lower() and p.title.lower() == job.title.lower() and p.job_id != job.job_id
            ]
            if len(same_company_title) >= 2:
                job.is_ghost_job = True
                score -= 0.20

        # 5. Completeness check
        word_count = len(desc.split())
        if word_count < 30:
            score -= 0.30
        elif word_count < 60:
            score -= 0.15

        if not job.location and not job.country:
            score -= 0.10

        # Bounds: 0.0 <= score <= 1.0
        job.quality_score = max(0.0, min(1.0, round(score, 2)))
        return job

    async def run(self, input_data: Any) -> Any:
        if isinstance(input_data, JobRecord):
            return self.assess_quality(input_data)
        elif isinstance(input_data, list):
            return [self.assess_quality(item) for item in input_data if isinstance(item, JobRecord)]
        return input_data
