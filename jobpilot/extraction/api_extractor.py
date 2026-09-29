"""
API Extractor for JobPilot AI.
Dispatches extraction requests to ATS board connectors (Greenhouse, Lever, Remotive, Adzuna)
and aggregates structured JobRecords.
"""

from typing import List, Optional
from urllib.parse import urlparse
from jobpilot.core.schemas import JobRecord
from jobpilot.discovery.greenhouse import GreenhouseSource
from jobpilot.discovery.lever import LeverSource
from jobpilot.discovery.remotive import RemotiveSource
from jobpilot.discovery.adzuna import AdzunaSource


class APIExtractor:
    """Unified handler for structured job board API extractions."""

    def __init__(self):
        self.greenhouse = GreenhouseSource()
        self.lever = LeverSource()
        self.remotive = RemotiveSource()
        self.adzuna = AdzunaSource()

    async def extract_from_url(self, url: str) -> List[JobRecord]:
        """Detect ATS domain and query appropriate API if possible."""
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        path_parts = [p for p in parsed.path.split("/") if p]

        # Greenhouse: boards.greenhouse.io/{board}
        if "greenhouse.io" in netloc and path_parts:
            board_token = path_parts[0]
            return await self.greenhouse.fetch_board_jobs(board_token)

        # Lever: jobs.lever.co/{site}
        if "lever.co" in netloc and path_parts:
            site_name = path_parts[0]
            return await self.lever.fetch_site_jobs(site_name)

        return []
