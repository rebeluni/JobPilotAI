"""
Tests for SearXNG Connector and QueryBuilder (Phase 2).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jobpilot.discovery.query_builder import QueryBuilder
from jobpilot.discovery.searxng import SearXNGSource
from jobpilot.core.schemas import RemotePolicy


def test_query_builder_ats_queries():
    """Verify ATS queries include operator, role keywords, and country."""
    qb = QueryBuilder()
    queries = qb.build_ats_queries(
        role_keywords=["AI Engineer", "LLM Developer"],
        countries=["Germany"],
        ats_operators=["site:boards.greenhouse.io"],
        remote=True,
    )
    assert len(queries) == 1
    assert "site:boards.greenhouse.io" in queries[0]
    assert '"AI Engineer"' in queries[0]
    assert '"Germany"' in queries[0]
    assert '"Remote"' in queries[0]


def test_query_builder_immigration_queries():
    """Verify immigration queries include visa sponsorship terms for foreign countries."""
    qb = QueryBuilder()
    queries = qb.build_immigration_queries(
        role_keywords=["AI Engineer"],
        countries=["Germany", "India"],
    )
    # India is excluded from international sponsorship queries
    assert len(queries) == 1
    assert "visa sponsorship" in queries[0]
    assert "Germany" in queries[0]


def test_searxng_heuristic_parsing():
    """Verify SearXNG item parsing extracts company, title, remote policy, and country."""
    source = SearXNGSource()
    raw_item = {
        "title": "Machine Learning Engineer at DeepMind - Remote (Germany)",
        "url": "https://boards.greenhouse.io/deepmind/jobs/998877",
        "content": "Join our team in Berlin or work remote. Building frontier generative models.",
    }
    job = source._parse_result_item(raw_item, "AI Engineer Germany")
    assert job is not None
    assert job.company == "DeepMind"
    assert "Machine Learning Engineer" in job.title
    assert job.remote_policy == RemotePolicy.REMOTE
    assert job.country == "Germany"
    assert job.source == "searxng"


@pytest.mark.asyncio
async def test_searxng_mock_search():
    """Verify SearXNGSource search execution with mocked HTTP response."""
    source = SearXNGSource(base_url="http://mock-searxng:8080", request_delay=0.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "AI Solutions Architect at Mistral AI",
                "url": "https://jobs.lever.co/mistral/123",
                "content": "Looking for applied AI engineer in Paris or London.",
            }
        ]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await source.search("AI Engineer UK")
        assert len(jobs) == 1
        assert jobs[0].company == "Mistral AI"
        assert jobs[0].job_url == "https://jobs.lever.co/mistral/123"
