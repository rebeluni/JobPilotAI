"""
Greenhouse Public Board API Connector for JobPilot AI.
Extracts open roles directly from company Greenhouse boards without scraping.
Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
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


@PluginRegistry.register_source("greenhouse")
class GreenhouseSource(BaseDiscoverySource):
    """Discovery connector for company Greenhouse job boards."""

    stage_name: str = "greenhouse"

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def fetch_board_jobs(self, board_token: str) -> List[JobRecord]:
        """Fetch all public job postings for a specific company Greenhouse board."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []

        jobs = data.get("jobs", [])
        records: List[JobRecord] = []
        company_name = board_token.capitalize()

        for j in jobs:
            title = j.get("title", "").strip()
            job_url = j.get("absolute_url", "").strip()
            raw_content = j.get("content", "")
            location_name = j.get("location", {}).get("name", "")

            # Strip HTML from content
            soup = BeautifulSoup(raw_content, "lxml")
            desc = soup.get_text(separator="\n", strip=True)

            salary_min, salary_max, currency = parse_salary(desc)
            exp_min, exp_max = parse_experience(desc)
            skills = extract_skills(desc)

            remote_policy = RemotePolicy.UNKNOWN
            loc_lower = f"{location_name} {title} {desc[:300]}".lower()
            if "remote" in loc_lower:
                remote_policy = RemotePolicy.REMOTE
            elif "hybrid" in loc_lower:
                remote_policy = RemotePolicy.HYBRID

            job_id = f"gh_{compute_url_hash(job_url)[:24]}"
            records.append(JobRecord(
                job_id=job_id,
                company=company_name,
                title=title,
                description=desc,
                location=location_name or None,
                remote_policy=remote_policy,
                employment_type=EmploymentType.FULL_TIME,
                salary_min=salary_min,
                salary_max=salary_max,
                currency=currency,
                experience_min=exp_min,
                experience_max=exp_max,
                skills=skills,
                job_url=job_url,
                source="greenhouse_api",
                date_posted=j.get("updated_at"),
                date_found=utcnow_str(),
                quality_score=0.95,
            ))

        return records

    async def search(self, query: str, limit: int = 20) -> List[JobRecord]:
        """Search given a company board token."""
        return await self.fetch_board_jobs(query.strip())
