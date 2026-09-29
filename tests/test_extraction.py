"""
Tests for Extraction and Normalization Pipeline (Phase 3).
Validates salary parsing, experience extraction, skill extraction,
HTML parsing, ATS API ingestion, and JobQualityChecker.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jobpilot.extraction.normalizer import parse_salary, parse_experience, extract_skills
from jobpilot.extraction.html_extractor import HTMLExtractor
from jobpilot.extraction.quality_checker import JobQualityChecker
from jobpilot.core.schemas import JobRecord, RemotePolicy
from jobpilot.discovery.greenhouse import GreenhouseSource
from jobpilot.discovery.lever import LeverSource
from jobpilot.discovery.remotive import RemotiveSource


def test_parse_salary_inr():
    """Verify INR LPA and Lakhs salary parsing."""
    s_min, s_max, curr = parse_salary("Compensation: ₹18 - 25 LPA based on experience.")
    assert s_min == 1800000.0
    assert s_max == 2500000.0
    assert curr == "INR"

    s_min2, s_max2, curr2 = parse_salary("Offering 15 Lakhs per annum.")
    assert s_min2 == 1500000.0
    assert s_max2 == 1500000.0
    assert curr2 == "INR"


def test_parse_salary_usd():
    """Verify USD range and k-shorthand parsing."""
    s_min, s_max, curr = parse_salary("Salary Range: $120k - $160k USD annually")
    assert s_min == 120000.0
    assert s_max == 160000.0
    assert curr == "USD"

    s_min2, s_max2, curr2 = parse_salary("Base salary: $90,000 - $115,000")
    assert s_min2 == 90000.0
    assert s_max2 == 115000.0
    assert curr2 == "USD"


def test_parse_salary_eur_and_gbp():
    """Verify EUR and GBP parsing."""
    s_min, s_max, curr = parse_salary("Package: €50,000 - €70,000 in Munich")
    assert s_min == 50000.0
    assert s_max == 70000.0
    assert curr == "EUR"

    s_min2, s_max2, curr2 = parse_salary("Competitive: £55k - £70k per year")
    assert s_min2 == 55000.0
    assert s_max2 == 70000.0
    assert curr2 == "GBP"


def test_parse_salary_unknown():
    """Verify unspecified or competitive compensation returns None."""
    s_min, s_max, curr = parse_salary("Competitive salary depending on experience, full health insurance.")
    assert s_min is None
    assert s_max is None
    assert curr is None


def test_parse_experience():
    """Verify range and minimum experience parsing."""
    e_min, e_max = parse_experience("Requires 1-3 years of hands-on software development.")
    assert e_min == 1
    assert e_max == 3

    e_min2, e_max2 = parse_experience("Must have 2+ years of LLM engineering experience.")
    assert e_min2 == 2
    assert e_max2 is None

    e_min3, e_max3 = parse_experience("At least 3 years experience building data pipelines.")
    assert e_min3 == 3
    assert e_max3 is None


def test_extract_skills():
    """Verify extraction of known candidate and technical skills."""
    text = "We are seeking an engineer skilled in Python, SQL, Generative AI, RAG pipelines, Make.com, and Docker."
    skills = extract_skills(text)
    assert "Python" in skills
    assert "SQL" in skills
    assert "Generative AI" in skills
    assert "RAG" in skills
    assert "Make.com" in skills
    assert "Docker" in skills


def test_html_extractor_structured_page():
    """Verify HTMLExtractor processes HTML into valid JobRecord."""
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>AI Solutions Engineer - Cohere Careers</title>
        <meta property="og:title" content="AI Solutions Engineer" />
        <meta property="og:site_name" content="Cohere" />
      </head>
      <body>
        <div class="job-description">
          <h1>AI Solutions Engineer</h1>
          <p>Location: London, UK (Hybrid)</p>
          <p>Salary: £65,000 - £85,000</p>
          <p>Requirements: 1-3 years experience with Python, LLMs, and REST APIs.</p>
        </div>
      </body>
    </html>
    """
    extractor = HTMLExtractor()
    job = extractor.extract(html, "https://cohere.com/careers/ai-solutions-engineer")
    assert job is not None
    assert job.company == "Cohere"
    assert job.title == "AI Solutions Engineer"
    assert job.remote_policy == RemotePolicy.HYBRID
    assert job.country == "UK"
    assert job.salary_min == 65000.0
    assert job.salary_max == 85000.0
    assert job.currency == "GBP"
    assert job.experience_min == 1
    assert job.experience_max == 3
    assert "Python" in job.skills
    assert "LLMs" in job.skills


def test_quality_checker_expired_job():
    """Verify JobQualityChecker catches expired postings."""
    checker = JobQualityChecker()
    job = JobRecord(
        job_id="job_exp_1",
        company="Startup AI",
        title="AI Engineer",
        description="Thank you for your interest. This position has been filled and is no longer available.",
        job_url="https://example.com/job/closed",
        source="searxng",
        date_found="2026-09-29T10:00:00Z",
    )
    checked = checker.assess_quality(job)
    assert checked.is_expired is True
    assert checked.quality_score < 0.70


def test_quality_checker_scam_signals():
    """Verify JobQualityChecker penalizes suspicious scam patterns."""
    checker = JobQualityChecker()
    job = JobRecord(
        job_id="job_scam_1",
        company="Shady Corp",
        title="Junior Python Assistant",
        description="Work from home! We will send you a cashier's check. Please wire transfer $200 for equipment.",
        job_url="https://example.com/job/scam",
        source="searxng",
        date_found="2026-09-29T10:00:00Z",
    )
    checked = checker.assess_quality(job)
    assert checked.quality_score <= 0.30


def test_quality_checker_ghost_job():
    """Verify JobQualityChecker detects reposted ghost postings."""
    checker = JobQualityChecker()
    existing = [
        JobRecord(
            job_id="old_1", company="Ghost AI", title="Data Analyst",
            job_url="https://ghost.example/1", source="searxng", date_found="2026-06-01T00:00:00Z"
        ),
        JobRecord(
            job_id="old_2", company="Ghost AI", title="Data Analyst",
            job_url="https://ghost.example/2", source="searxng", date_found="2026-08-01T00:00:00Z"
        ),
    ]
    new_job = JobRecord(
        job_id="new_1", company="Ghost AI", title="Data Analyst",
        description="Standard data analyst role with SQL and Python.",
        job_url="https://ghost.example/3", source="searxng", date_found="2026-09-29T00:00:00Z"
    )
    checked = checker.assess_quality(new_job, existing_postings=existing)
    assert checked.is_ghost_job is True


@pytest.mark.asyncio
async def test_greenhouse_connector_mock():
    """Verify Greenhouse connector decodes board jobs properly."""
    source = GreenhouseSource()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobs": [
            {
                "title": "Machine Learning Engineer",
                "absolute_url": "https://boards.greenhouse.io/scaleai/jobs/112233",
                "content": "<p>Build data pipelines and generative AI models with Python and Docker. Salary: $130,000 - $160,000 USD. Remote.</p>",
                "location": {"name": "Remote, US"},
            }
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await source.fetch_board_jobs("scaleai")
        assert len(jobs) == 1
        assert jobs[0].company == "Scaleai"
        assert jobs[0].title == "Machine Learning Engineer"
        assert jobs[0].remote_policy == RemotePolicy.REMOTE
        assert jobs[0].salary_min == 130000.0
        assert "Python" in jobs[0].skills


@pytest.mark.asyncio
async def test_lever_connector_mock():
    """Verify Lever connector parses job postings."""
    source = LeverSource()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "text": "Automation Specialist",
            "hostedUrl": "https://jobs.lever.co/zapier/445566",
            "categories": {"location": "Remote", "workplaceType": "remote"},
            "descriptionPlain": "Build Make.com, Power Automate, and Python workflows. 1-2 years experience.",
        }
    ]
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await source.fetch_site_jobs("zapier")
        assert len(jobs) == 1
        assert jobs[0].company == "Zapier"
        assert jobs[0].title == "Automation Specialist"
        assert jobs[0].remote_policy == RemotePolicy.REMOTE
        assert jobs[0].experience_min == 1
        assert jobs[0].experience_max == 2


@pytest.mark.asyncio
async def test_remotive_connector_mock():
    """Verify Remotive connector parses remote postings."""
    source = RemotiveSource()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobs": [
            {
                "title": "AI Integration Developer",
                "company_name": "Distributed AI",
                "url": "https://remotive.com/job/987",
                "description": "<p>Develop agentic tools using Python, REST APIs, and LLMs.</p>",
                "candidate_required_location": "Worldwide",
                "salary": "$90,000 - $120,000",
                "tags": ["python", "ai", "llm"],
            }
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await source.search(query="AI")
        assert len(jobs) == 1
        assert jobs[0].company == "Distributed AI"
        assert jobs[0].remote_policy == RemotePolicy.REMOTE
        assert jobs[0].salary_min == 90000.0
        assert "Python" in jobs[0].skills
