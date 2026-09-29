"""
Contract test for JobRecord schema.
Ensures that all producers (discovery, extraction) output conforming data
and consumers (matching, immigration, applications) receive expected types.
"""

import pytest
from pydantic import ValidationError
from jobpilot.core.schemas import (
    JobRecord,
    RemotePolicy,
    EmploymentType,
    VisaStatus,
    MatchStatus,
    RoleTier,
)


def test_job_record_valid_creation():
    """Verify JobRecord creates properly with full valid data."""
    job_data = {
        "job_id": "test_sha256_hash_123",
        "company": "DeepMind Innovations",
        "title": "AI Solutions Engineer",
        "description": "Looking for an AI engineer to develop agentic workflows with LLMs and RAG pipelines.",
        "location": "Bengaluru, Karnataka",
        "country": "India",
        "remote_policy": "HYBRID",
        "employment_type": "FULL_TIME",
        "salary_min": 1800000.0,
        "salary_max": 2500000.0,
        "currency": "INR",
        "experience_min": 1,
        "experience_max": 3,
        "skills": ["Python", "Generative AI", "RAG", "LLMs"],
        "role_family": "AI_SOLUTIONS_ENGINEER",
        "role_tier": "EXACT",
        "job_url": "https://example.com/careers/ai-engineer-123",
        "source": "searxng",
        "date_posted": "2026-09-28",
        "date_found": "2026-09-29T10:00:00Z",
        "is_expired": False,
        "is_ghost_job": False,
        "quality_score": 0.95,
        "visa_status": "INDIA",
        "sponsor_verified": False,
        "relocation_support": False,
    }
    job = JobRecord(**job_data)
    assert job.job_id == "test_sha256_hash_123"
    assert job.company == "DeepMind Innovations"
    assert job.remote_policy == RemotePolicy.HYBRID
    assert job.employment_type == EmploymentType.FULL_TIME
    assert job.visa_status == VisaStatus.INDIA
    assert job.role_tier == RoleTier.EXACT
    assert "Python" in job.skills


def test_job_record_defaults():
    """Verify default values when optional fields are omitted."""
    job = JobRecord(
        job_id="job_minimal_1",
        company="Startup Co",
        title="Junior AI Engineer",
        job_url="https://example.com/job/1",
        source="greenhouse",
        date_found="2026-09-29T10:00:00Z",
    )
    assert job.remote_policy == RemotePolicy.UNKNOWN
    assert job.employment_type == EmploymentType.UNKNOWN
    assert job.skills == []
    assert job.visa_status == VisaStatus.UNCLEAR
    assert job.quality_score == 1.0
    assert job.is_expired is False
    assert job.is_ghost_job is False
    assert job.status == "NEW"


def test_job_record_invalid_missing_required():
    """Verify validation fails if required fields like job_url or title are missing."""
    with pytest.raises(ValidationError):
        JobRecord(
            job_id="job_bad",
            company="Startup Co",
            # missing title, job_url, source, date_found
        )


def test_job_record_enum_serialization():
    """Verify enums dump and parse cleanly in JSON."""
    job = JobRecord(
        job_id="job_enum_test",
        company="Acme Corp",
        title="ML Engineer",
        job_url="https://acme.com/jobs/1",
        source="adzuna",
        date_found="2026-09-29T10:00:00Z",
        remote_policy=RemotePolicy.REMOTE,
        visa_status=VisaStatus.SPONSORSHIP_POSSIBLE,
        match_status=MatchStatus.GOOD_MATCH,
    )
    json_data = job.model_dump()
    assert json_data["remote_policy"] == "REMOTE"
    assert json_data["visa_status"] == "SPONSORSHIP_POSSIBLE"
    assert json_data["match_status"] == "GOOD_MATCH"

    # Re-hydrate from dict
    restored = JobRecord(**json_data)
    assert restored.remote_policy == RemotePolicy.REMOTE
    assert restored.visa_status == VisaStatus.SPONSORSHIP_POSSIBLE
