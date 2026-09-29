"""
Adzuna API Connector for JobPilot AI.
Extracts jobs across India, UK, Germany, Australia, and Canada using Adzuna API.
Requires ADZUNA_APP_ID and ADZUNA_APP_KEY if configured; returns empty gracefully if unset.
"""

import os
from typing import Any, Dict, List, Optional
import httpx

from jobpilot.discovery.base import BaseDiscoverySource
from jobpilot.core.registry import PluginRegistry
from jobpilot.core.schemas import JobRecord, RemotePolicy, EmploymentType
from jobpilot.extraction.normalizer import parse_experience, extract_skills
from jobpilot.database.models import utcnow_str
from jobpilot.discovery.deduplicator import compute_url_hash


COUNTRY_CODE_MAP = {
    "india": "in",
    "germany": "de",
    "uk": "gb",
    "united kingdom": "gb",
    "australia": "au",
    "canada": "ca",
    "netherlands": "nl",
}


@PluginRegistry.register_source("adzuna")
class AdzunaSource(BaseDiscoverySource):
    """Discovery connector for Adzuna job search API."""

    stage_name: str = "adzuna"

    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None, timeout: float = 20.0):
        self.app_id = app_id or os.environ.get("ADZUNA_APP_ID")
        self.app_key = app_key or os.environ.get("ADZUNA_APP_KEY")
        self.timeout = timeout

    async def search(self, query: str = "", country: str = "india", limit: int = 20) -> List[JobRecord]:
        """Query Adzuna search endpoint."""
        if not self.app_id or not self.app_key:
            # Opt-in API: gracefully returns empty if keys are not configured
            return []

        c_code = COUNTRY_CODE_MAP.get(country.lower(), "in")
        url = f"https://api.adzuna.com/v1/api/jobs/{c_code}/search/1"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": query,
            "results_per_page": limit,
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []

        results = data.get("results", [])
        records: List[JobRecord] = []

        for j in results:
            title = j.get("title", "").strip()
            company = j.get("company", {}).get("display_name", "Unknown Company")
            job_url = j.get("redirect_url", "").strip()
            desc = j.get("description", "").strip()
            location = j.get("location", {}).get("display_name", country.capitalize())

            salary_min = j.get("salary_min")
            salary_max = j.get("salary_max")
            currency = "INR" if c_code == "in" else ("GBP" if c_code == "gb" else "EUR")

            exp_min, exp_max = parse_experience(desc)
            skills = extract_skills(desc)

            remote_policy = RemotePolicy.UNKNOWN
            if "remote" in desc.lower() or "remote" in title.lower():
                remote_policy = RemotePolicy.REMOTE

            job_id = f"adz_{compute_url_hash(job_url)[:24]}"
            records.append(JobRecord(
                job_id=job_id,
                company=company,
                title=title,
                description=desc,
                location=location,
                country=country.capitalize(),
                remote_policy=remote_policy,
                employment_type=EmploymentType.FULL_TIME,
                salary_min=float(salary_min) if salary_min else None,
                salary_max=float(salary_max) if salary_max else None,
                currency=currency,
                experience_min=exp_min,
                experience_max=exp_max,
                skills=skills,
                job_url=job_url,
                source="adzuna_api",
                date_posted=j.get("created"),
                date_found=utcnow_str(),
                quality_score=0.85,
            ))

        return records
