"""
Remotive Public API Discovery Connector for JobPilot AI.
Extracts global remote-first software and AI opportunities.
Endpoint: https://remotive.com/api/remote-jobs
"""

from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import httpx

from jobpilot.discovery.base import BaseDiscoverySource
from jobpilot.core.registry import PluginRegistry
from jobpilot.core.schemas import JobRecord, RemotePolicy, EmploymentType
from jobpilot.extraction.normalizer import parse_salary, parse_experience, extract_skills
from jobpilot.database.models import utcnow_str
from jobpilot.discovery.deduplicator import compute_url_hash


@PluginRegistry.register_source("remotive")
class RemotiveSource(BaseDiscoverySource):
    """Discovery connector for Remotive remote jobs API."""

    stage_name: str = "remotive"

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def search(self, query: str = "", limit: int = 30) -> List[JobRecord]:
        """Fetch remote jobs matching search terms."""
        url = "https://remotive.com/api/remote-jobs"
        params = {"limit": limit}
        if query:
            params["search"] = query

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []

        jobs = data.get("jobs", [])
        records: List[JobRecord] = []

        for j in jobs[:limit]:
            title = j.get("title", "").strip()
            company = j.get("company_name", "").strip()
            job_url = j.get("url", "").strip()
            raw_desc = j.get("description", "")
            location_str = j.get("candidate_required_location", "Worldwide")
            tags = j.get("tags", [])

            soup = BeautifulSoup(raw_desc, "lxml")
            desc = soup.get_text(separator="\n", strip=True)

            salary_str = j.get("salary", "")
            salary_min, salary_max, currency = parse_salary(f"{salary_str} {desc}")
            exp_min, exp_max = parse_experience(desc)
            skills = extract_skills(f"{' '.join(tags)} {desc}")

            job_id = f"rem_{compute_url_hash(job_url)[:24]}"
            records.append(JobRecord(
                job_id=job_id,
                company=company,
                title=title,
                description=desc,
                location=location_str,
                country="Remote" if "worldwide" in location_str.lower() else location_str,
                remote_policy=RemotePolicy.REMOTE,
                employment_type=EmploymentType.FULL_TIME,
                salary_min=salary_min,
                salary_max=salary_max,
                currency=currency,
                experience_min=exp_min,
                experience_max=exp_max,
                skills=skills,
                job_url=job_url,
                source="remotive_api",
                date_posted=j.get("publication_date"),
                date_found=utcnow_str(),
                quality_score=0.90,
            ))

        return records
