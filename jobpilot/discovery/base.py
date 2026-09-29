"""
Base discovery source interface for JobPilot AI.
All discovery connectors (SearXNG, Greenhouse, Lever, etc.) inherit from this.
"""

from abc import abstractmethod
from typing import Any, List
from jobpilot.core.pipeline import PipelineStage
from jobpilot.core.schemas import JobRecord


class BaseDiscoverySource(PipelineStage):
    """Abstract base for discovery sources producing JobRecords."""

    stage_name: str = "discovery_source"

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> List[JobRecord]:
        """Execute a single search query and return raw discovered JobRecords."""
        pass

    async def run(self, input_data: Any) -> List[JobRecord]:
        """
        Standard PipelineStage run implementation.
        Takes query string or list of query strings, returns aggregated JobRecords.
        """
        if isinstance(input_data, str):
            return await self.search(input_data)
        elif isinstance(input_data, list):
            results: List[JobRecord] = []
            for q in input_data:
                batch = await self.search(str(q))
                results.extend(batch)
            return results
        return []
