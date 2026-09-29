"""
Lever Public Postings API Connector for JobPilot AI.
Extracts open roles directly from company Lever sites.
Endpoint: https://api.lever.co/v0/postings/{site}?mode=json
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


@PluginRegistry.register_source("lever")
class LeverSource(BaseDiscoverySource):
    """Discovery connector for company Lever job sites."""

    stage_name: str = "lever"

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def fetch_site_jobs(self, site_name: str) -> List[JobRecord]:
        """Fetch all public job postings for a specific company Lever site."""
        url = f"https://api.lever.co/v0/postings/{site_name}?mode=json"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []

        records: List[JobRecord] = []
        company_name = site_name.capitalize()

        for j in data:
            title = j.get("text", "").strip()
            job_url = j.get("hostedUrl", "").strip()
            categories = j.get("categories", {})
            location_name = categories.get("location", "")
            workplace_type = categories.get("workplaceType", "").lower()

            desc_parts = [j.get("descriptionPlain", "")]
            for list_item in j.get("lists", []):
                desc_parts.append(list_item.get("text", ""))
                desc_parts.append(list_item.get("content", ""))
            desc = "\n".join(filter(None, desc_parts)).strip()

            salary_min, salary_max, currency = parse_salary(desc)
            exp_min, exp_max = parse_experience(desc)
            skills = extract_skills(desc)

            remote_policy = RemotePolicy.UNKNOWN
            if "remote" in workplace_type or "remote" in location_name.lower():
                remote_policy = RemotePolicy.REMOTE
            elif "hybrid" in workplace_type or "hybrid" in location_name.lower():
                remote_policy = RemotePolicy.HYBRID
            elif "onsite" in workplace_type or "on-site" in workplace_type:
                remote_policy = RemotePolicy.ONSITE

            job_id = f"lev_{compute_url_hash(job_url)[:24]}"
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
                source="lever_api",
                date_found=utcnow_str(),
                quality_score=0.95,
            ))

        return records

    async def search(self, query: str, limit: int = 20) -> List[JobRecord]:
        return await self.fetch_site_jobs(query.strip())
