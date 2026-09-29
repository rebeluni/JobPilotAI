"""
Contract test for MatchResult schema.
Ensures that matching outputs adhere to strict score bounds, enum states, and required breakdown fields.
"""

import pytest
from pydantic import ValidationError
from jobpilot.core.schemas import MatchResult, MatchStatus


def test_match_result_valid():
    """Verify MatchResult instantiates with score in [0.0, 1.0] and dimension breakdown."""
    mr = MatchResult(
        job_id="job_match_100",
        match_score=0.82,
        match_status=MatchStatus.STRONG_MATCH,
        dimension_scores={
            "role_relevance": 0.90,
            "technical_skill": 0.85,
            "experience": 0.70,
            "location_remote": 1.0,
            "immigration": 1.0,
            "seniority": 0.80,
            "education": 0.90,
        },
        pros=["Strong alignment with Python, LLMs, and RAG", "Matches target role family"],
        cons=["Requires 2-3 years, candidate has ~1 year"],
        concerns=["Soft penalty applied on experience"],
        recommended_variant="ai_engineer",
        optimizer_recommended=True,
        reasoning="Overall strong candidate match with high skill synergy.",
    )
    assert mr.match_score == 0.82
    assert mr.match_status == MatchStatus.STRONG_MATCH
    assert mr.dimension_scores["role_relevance"] == 0.90
    assert len(mr.pros) == 2
    assert mr.optimizer_recommended is True


def test_match_result_score_bounds():
    """Verify match_score outside 0.0 to 1.0 raises ValidationError."""
    with pytest.raises(ValidationError):
        MatchResult(
            job_id="job_bad_score_high",
            match_score=1.25,  # > 1.0
            match_status=MatchStatus.STRONG_MATCH,
        )

    with pytest.raises(ValidationError):
        MatchResult(
            job_id="job_bad_score_low",
            match_score=-0.1,  # < 0.0
            match_status=MatchStatus.NO_MATCH,
        )


def test_match_result_defaults():
    """Verify defaults for pros, cons, and dimension scores."""
    mr = MatchResult(
        job_id="job_min_match",
        match_score=0.68,
        match_status=MatchStatus.GOOD_MATCH,
    )
    assert mr.dimension_scores == {}
    assert mr.pros == []
    assert mr.cons == []
    assert mr.concerns == []
    assert mr.recommended_variant == "default"
    assert mr.optimizer_recommended is False
    assert mr.reasoning == ""
