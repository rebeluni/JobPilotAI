"""
Unit and integration tests for Matching Engine (Phase 4).
Tests semantic pre-ranking, dimension scoring, soft penalty for experience gap,
hard filters, feedback loop, and calibrator.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from jobpilot.matching.embedder import JobEmbedder, cosine_similarity
from jobpilot.matching.scorer import DimensionScorer
from jobpilot.matching.filters import check_hard_filters, calculate_experience_penalty
from jobpilot.matching.engine import MatchingEngine
from jobpilot.matching.feedback import FeedbackLoop
from jobpilot.matching.calibration import MatchCalibrator
from jobpilot.core.schemas import JobRecord, MatchStatus, RemotePolicy, VisaStatus


@pytest.fixture
def sample_profile():
    return {
        "personal": {"full_name": "Ankita Yadav"},
        "education": [{"degree": "B.Tech", "field": "Artificial Intelligence & Data Science"}],
        "experience": {"total_years_professional": 1},
        "skills": {
            "programming": ["Python", "SQL", "JavaScript"],
            "ai_ml": ["LLMs", "RAG", "Generative AI", "AI Agents"],
            "automation": ["Make.com", "Power Automate"],
        },
        "preferences": {
            "target_role_families": ["AI_ENGINEER", "AI_AUTOMATION", "SOLUTIONS_ENGINEER"],
            "target_countries": ["India", "Germany", "UK"],
        },
    }


def test_cosine_similarity():
    """Verify vector cosine math."""
    v1 = [1.0, 0.0, 1.0]
    v2 = [1.0, 0.0, 1.0]
    assert cosine_similarity(v1, v2) == 1.0

    v_ortho = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v_ortho) == 0.0


def test_experience_soft_penalty():
    """Verify that experience gap applies soft penalty and generates concern, NOT hard rejection."""
    # 1 year candidate vs 3 years requirement
    penalty, concern = calculate_experience_penalty(required_years_min=3, candidate_years=1, penalty_per_year=0.15)
    assert penalty == 0.30
    assert concern is not None
    assert "Soft penalty of -0.30" in concern

    # 1 year candidate vs 1 year requirement -> 0 penalty
    pen_zero, concern_zero = calculate_experience_penalty(required_years_min=1, candidate_years=1)
    assert pen_zero == 0.0
    assert concern_zero is None


def test_hard_filters():
    """Verify hard filter rejects avoided roles and incompatible stacks."""
    # DevOps role must be rejected
    devops_job = JobRecord(
        job_id="j_devops",
        company="Cloud Services",
        title="Senior DevOps Engineer (Kubernetes, Terraform)",
        job_url="https://cloud.com/job/1",
        source="searxng",
        date_found="2026-09-29T10:00:00Z",
    )
    rej, reason = check_hard_filters(devops_job)
    assert rej is True
    assert "avoided career category" in reason

    # Java/Spring primary role without AI or Python
    java_job = JobRecord(
        job_id="j_java",
        company="Enterprise Banking",
        title="Senior Java Spring Boot Backend Developer",
        description="Develop microservices in Java 17 and Spring Cloud.",
        job_url="https://bank.com/job/2",
        source="searxng",
        date_found="2026-09-29T10:00:00Z",
    )
    rej_java, reason_java = check_hard_filters(java_job)
    assert rej_java is True
    assert "java" in reason_java.lower()

    # AI Engineer role must pass hard filter
    ai_job = JobRecord(
        job_id="j_ai",
        company="GenAI Labs",
        title="AI Engineer",
        description="Build LLM applications and RAG systems using Python.",
        job_url="https://genai.com/job/3",
        source="searxng",
        date_found="2026-09-29T10:00:00Z",
    )
    rej_ai, _ = check_hard_filters(ai_job)
    assert rej_ai is False


def test_dimension_scorer_strong_match(sample_profile):
    """Verify ideal AI Engineer job receives STRONG_MATCH score."""
    scorer = DimensionScorer()
    job = JobRecord(
        job_id="j_strong",
        company="OpenAI Partner",
        title="Generative AI Engineer",
        description="Looking for an AI engineer to develop agentic LLM workflows and RAG pipelines.",
        location="Mumbai, India",
        country="India",
        remote_policy=RemotePolicy.HYBRID,
        experience_min=1,
        skills=["Python", "LLMs", "RAG", "Generative AI"],
        job_url="https://partner.com/job/1",
        source="greenhouse",
        date_found="2026-09-29T10:00:00Z",
        visa_status=VisaStatus.INDIA,
    )
    score, status, dim_scores, pros, cons, concerns = scorer.score_job(job, sample_profile)
    assert score >= 0.80
    assert status == MatchStatus.STRONG_MATCH
    assert dim_scores["role_relevance"] >= 0.90
    assert dim_scores["technical_skill"] >= 0.85
    assert dim_scores["immigration"] == 1.0
    assert len(pros) > 0


def test_dimension_scorer_stretch_gap(sample_profile):
    """Verify job with 4 years experience required gets soft penalty but remains in STRETCH or GOOD match."""
    scorer = DimensionScorer()
    job = JobRecord(
        job_id="j_stretch",
        company="Scale Tech",
        title="Applied AI Specialist",
        description="Build LLM pipelines.",
        country="India",
        experience_min=4,  # Candidate has ~1
        skills=["Python", "LLMs"],
        job_url="https://scale.com/job/1",
        source="searxng",
        date_found="2026-09-29T10:00:00Z",
    )
    score, status, dim_scores, pros, cons, concerns = scorer.score_job(job, sample_profile)
    assert len(concerns) > 0
    assert "Soft penalty" in concerns[0]
    assert dim_scores["experience"] < 0.60
    assert status != MatchStatus.NO_MATCH


@pytest.mark.asyncio
async def test_matching_engine_batch():
    """Verify MatchingEngine processes batch and populates MatchResults."""
    engine = MatchingEngine()
    jobs = [
        JobRecord(
            job_id="batch_j1",
            company="AI Innovations",
            title="AI Engineer",
            skills=["Python", "LLMs", "RAG"],
            job_url="https://ai.com/job/1",
            source="searxng",
            date_found="2026-09-29T10:00:00Z",
            country="India",
        ),
        JobRecord(
            job_id="batch_j2",
            company="DevOps Cloud",
            title="DevOps Engineer",
            job_url="https://devops.com/job/2",
            source="searxng",
            date_found="2026-09-29T10:00:00Z",
        ),
    ]
    results = await engine.match_batch(jobs)
    assert len(results) == 2
    # AI Engineer is top scored
    assert results[0].job_id == "batch_j1"
    assert results[0].match_score > 0.70
    assert results[0].recommended_variant == "ai_engineer"
    # DevOps is NO_MATCH
    assert results[1].job_id == "batch_j2"
    assert results[1].match_status == MatchStatus.NO_MATCH


def test_feedback_loop():
    """Verify thumbs up/down updates weights within [0.05, 0.40] bounds."""
    mock_repo = MagicMock()
    mock_job = MagicMock()
    mock_job.match_reasoning = '{"dimensions": {"technical_skill": 0.95, "role_relevance": 0.90}}'
    mock_repo.get_job.return_value = mock_job

    feedback_loop = FeedbackLoop(mock_repo)
    weights = {"role_relevance": 0.25, "technical_skill": 0.25, "experience": 0.20, "location_remote": 0.10, "immigration": 0.10, "seniority": 0.05, "education": 0.05}

    updated_up = feedback_loop.record_feedback("job_1", "THUMBS_UP", weights)
    assert updated_up["technical_skill"] >= 0.25
    assert sum(updated_up.values()) == pytest.approx(1.0, 0.01)

    updated_down = feedback_loop.record_feedback("job_1", "THUMBS_DOWN", weights)
    assert updated_down["technical_skill"] <= 0.25
    assert sum(updated_down.values()) == pytest.approx(1.0, 0.01)


@pytest.mark.asyncio
async def test_match_calibrator():
    """Verify Calibrator computes precision, recall, and accuracy."""
    engine = MatchingEngine()
    calibrator = MatchCalibrator(engine)

    good_job = JobRecord(
        job_id="calib_good",
        company="Cohere AI",
        title="AI Engineer",
        skills=["Python", "LLMs", "RAG"],
        country="India",
        job_url="https://cohere.com/1",
        source="searxng",
        date_found="2026-09-29T10:00:00Z",
    )
    bad_job = JobRecord(
        job_id="calib_bad",
        company="Infra Systems",
        title="Linux SysAdmin",
        job_url="https://infra.com/2",
        source="searxng",
        date_found="2026-09-29T10:00:00Z",
    )

    labeled_set = [
        {"job": good_job, "expected_label": "GOOD"},
        {"job": bad_job, "expected_label": "BAD"},
    ]

    metrics = await calibrator.evaluate_labeled_set(labeled_set)
    assert metrics["total_evaluated"] == 2
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
