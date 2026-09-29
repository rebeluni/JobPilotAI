"""
SearXNG Discovery Connector for JobPilot AI.
Interfaces with self-hosted or public SearXNG JSON API to query search engines
(Google, Bing, DuckDuckGo) without API fees or tracking.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx

from jobpilot.discovery.base import BaseDiscoverySource
from jobpilot.core.registry import PluginRegistry
from jobpilot.core.schemas import JobRecord, RemotePolicy, EmploymentType, RoleTier
from jobpilot.database.models import utcnow_str
from jobpilot.discovery.deduplicator import compute_url_hash


@PluginRegistry.register_source("searxng")
class SearXNGSource(BaseDiscoverySource):
    """SearXNG meta-search discovery provider."""

    stage_name: str = "searxng"

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        engines: Optional[List[str]] = None,
        timeout: float = 30.0,
        request_delay: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.engines = engines or ["google", "bing", "duckduckgo"]
        self.timeout = timeout
        self.request_delay = request_delay

    async def search(self, query: str, limit: int = 20) -> List[JobRecord]:
        """Execute search on SearXNG endpoint and convert results to JobRecords."""
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "format": "json",
            "engines": ",".join(self.engines),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.ConnectError:
                raise ConnectionError(
                    f"Could not connect to SearXNG at {self.base_url}. "
                    f"Ensure SearXNG is running (e.g. docker run -d -p 8080:8080 searxng/searxng)."
                )

        results = data.get("results", [])
        job_records: List[JobRecord] = []

        for item in results[:limit]:
            parsed_job = self._parse_result_item(item, query)
            if parsed_job:
                job_records.append(parsed_job)

        if self.request_delay > 0:
            await asyncio.sleep(self.request_delay)

        return job_records

    def _parse_result_item(self, item: Dict[str, Any], query: str) -> Optional[JobRecord]:
        """Parse raw SearXNG JSON result item into normalized JobRecord."""
        raw_title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        snippet = item.get("content", "").strip()

        if not url or not raw_title:
            return None

        # Extract company and job title from common title formats like:
        # "Senior AI Engineer at Acme Inc" or "Acme Inc - Machine Learning Specialist"
        company, title = self._extract_company_and_title(raw_title, url)

        # Detect remote policy from snippet or title
        combined_text = f"{raw_title} {snippet}".lower()
        remote_policy = RemotePolicy.UNKNOWN
        if "remote" in combined_text or "work from home" in combined_text:
            remote_policy = RemotePolicy.REMOTE
        elif "hybrid" in combined_text:
            remote_policy = RemotePolicy.HYBRID
        elif "on-site" in combined_text or "onsite" in combined_text:
            remote_policy = RemotePolicy.ONSITE

        # Deterministic Job ID from URL hash
        job_id = f"job_{compute_url_hash(url)[:24]}"

        # Country heuristic from query
        country = self._detect_country(query, combined_text)

        return JobRecord(
            job_id=job_id,
            company=company,
            title=title,
            description=snippet,
            location=country if country else None,
            country=country,
            remote_policy=remote_policy,
            employment_type=EmploymentType.FULL_TIME,
            job_url=url,
            source="searxng",
            date_found=utcnow_str(),
            quality_score=0.85,
        )

    def _extract_company_and_title(self, raw_title: str, url: str) -> tuple[str, str]:
        """Heuristic parser to separate job title from company name."""
        clean = re.sub(r"\s*[-|–—]\s*(Greenhouse|Lever|Ashby|Workday|Careers|Jobs).*", "", raw_title, flags=re.IGNORECASE)

        # Pattern: "Title at Company"
        match_at = re.search(r"^(.*?)\s+at\s+(.*?)$", clean, re.IGNORECASE)
        if match_at:
            title = match_at.group(1).strip()
            company_raw = match_at.group(2).strip()
            company = re.sub(r"\s*[-|–—]\s*(Remote|Hybrid|On-site|Onsite|Jobs|Careers|\(.*?\)|Germany|India|UK|United Kingdom|Canada|Australia|Singapore|UAE).*", "", company_raw, flags=re.IGNORECASE).strip()
            company = re.sub(r"\s*\(.*?\)$", "", company).strip()
            return company, title

        # Pattern: "Company - Title"
        if " - " in clean:
            parts = clean.split(" - ", 1)
            return parts[0].strip(), parts[1].strip()

        # Pattern: "Title | Company"
        if " | " in clean:
            parts = clean.split(" | ", 1)
            return parts[1].strip(), parts[0].strip()

        # Fallback from URL domain
        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split(".")
        if len(domain_parts) >= 2:
            fallback_company = domain_parts[-2].capitalize()
        else:
            fallback_company = "Unknown Company"

        return fallback_company, clean

    def _detect_country(self, query: str, text: str) -> Optional[str]:
        target_countries = ["India", "Germany", "Netherlands", "UK", "United Kingdom", "Canada", "Australia", "Singapore", "UAE"]
        for c in target_countries:
            if c.lower() in query.lower() or c.lower() in text:
                return "UK" if c in ("UK", "United Kingdom") else c
        return None

    async def health_check(self) -> bool:
        """Check if SearXNG service is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/")
                return resp.status_code == 200
        except Exception:
            return False
