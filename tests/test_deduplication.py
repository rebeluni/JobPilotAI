"""
Tests for 3-Level Job Deduplication Engine (Phase 2).
"""

from jobpilot.core.schemas import JobRecord
from jobpilot.discovery.deduplicator import (
    normalize_url,
    compute_url_hash,
    compute_content_hash,
    Deduplicator,
)


def test_normalize_url_strips_tracking():
    """Verify UTM and tracking parameters are cleaned from URL."""
    dirty_url = "https://boards.greenhouse.io/company/jobs/12345?utm_source=linkedin&utm_medium=job_post&ref=share#apply"
    clean = normalize_url(dirty_url)
    assert "utm_source" not in clean
    assert "ref" not in clean
    assert "#apply" not in clean
    assert clean == "https://boards.greenhouse.io/company/jobs/12345"


def test_url_hash_deterministic():
    """Verify hash consistency for equivalent URLs."""
    url1 = "https://jobs.lever.co/techco/abc-123/"
    url2 = "https://jobs.lever.co/techco/abc-123?utm_campaign=winter"
    assert compute_url_hash(url1) == compute_url_hash(url2)


def test_content_hash_normalization():
    """Verify normalization catches minor spacing and casing variations."""
    h1 = compute_content_hash("DeepMind Inc.", "AI Engineer", "India")
    h2 = compute_content_hash("deepmind inc", "ai engineer", "india")
    h3 = compute_content_hash("DeepMind, Inc", "  AI   Engineer ", "India")
    assert h1 == h2
    assert h1 == h3


def test_deduplicator_filters_duplicates():
    """Verify Deduplicator catches both URL and content duplicates."""
    job1 = JobRecord(
        job_id="j1",
        company="Alpha AI",
        title="Solutions Engineer",
        job_url="https://example.com/job/1",
        source="searxng",
        country="Germany",
        date_found="2026-09-29T10:00:00Z",
    )
    job2_url_dup = JobRecord(
        job_id="j2",
        company="Alpha AI Different Name",
        title="Different Title",
        job_url="https://example.com/job/1?utm_source=test",
        source="searxng",
        country="Germany",
        date_found="2026-09-29T10:00:00Z",
    )
    job3_content_dup = JobRecord(
        job_id="j3",
        company="Alpha AI",
        title="Solutions Engineer",
        job_url="https://different-aggregator.com/post/999",
        source="adzuna",
        country="Germany",
        date_found="2026-09-29T10:00:00Z",
    )
    job4_unique = JobRecord(
        job_id="j4",
        company="Beta AI",
        title="Solutions Engineer",
        job_url="https://beta.com/career/1",
        source="searxng",
        country="Germany",
        date_found="2026-09-29T10:00:00Z",
    )

    deduper = Deduplicator()
    unique, duplicates = deduper.filter_unique([job1, job2_url_dup, job3_content_dup, job4_unique])

    assert len(unique) == 2
    assert unique[0].job_id == "j1"
    assert unique[1].job_id == "j4"
    assert len(duplicates) == 2
    assert duplicates[0][0].job_id == "j2"
    assert duplicates[1][0].job_id == "j3"
