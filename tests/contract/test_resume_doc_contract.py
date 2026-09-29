"""
Contract test for ResumeDoc, CoverLetterDoc, ApplicationPackage, and Core Safety assertions.
Ensures document structures, package assembly, and strict safety rules are enforced.
"""

import pytest
from unittest.mock import MagicMock
from jobpilot.core.schemas import (
    ResumeDoc,
    CoverLetterDoc,
    ApplicationAnswer,
    ApplicationPackage,
    JobRecord,
    MatchResult,
    MatchStatus,
    OptimizerMode,
)
from jobpilot.core.safety import (
    SafetyViolation,
    assert_no_needs_user_input_in_required_fields,
    assert_no_legal_auto_answer,
    assert_optimizer_no_new_claims,
    assert_user_approved,
)
from jobpilot.core.registry import PluginRegistry
from jobpilot.core.pipeline import PipelineStage
from jobpilot.core.feature_flags import is_enabled


def test_resume_doc_structure():
    """Verify ResumeDoc schema fields and defaults."""
    doc = ResumeDoc(
        variant="ai_engineer",
        full_name="Ankita Yadav",
        contact_email="ankita@example.com",
        location="Mumbai, India",
        summary="AI and Automation Engineer with ~1 year experience in Generative AI, LLMs, and RAG.",
        skills={
            "programming": ["Python", "JavaScript", "SQL"],
            "ai_ml": ["LLMs", "RAG", "Generative AI"],
            "automation": ["Make.com", "Power Automate"],
        },
        experience=[
            {
                "employer": "Tech Solutions",
                "title": "AI Automation Specialist",
                "bullets": ["Engineered RAG pipelines utilizing vector search and LLMs."],
            }
        ],
        education=[
            {
                "degree": "B.Tech",
                "field": "Artificial Intelligence & Data Science",
            }
        ],
        optimizer_mode=OptimizerMode.SUGGEST,
        optimizer_diff=["Prioritized Python and LLM bullet points above workflow automation."],
    )
    assert doc.full_name == "Ankita Yadav"
    assert doc.optimizer_mode == OptimizerMode.SUGGEST
    assert len(doc.optimizer_diff) == 1
    assert "Python" in doc.skills["programming"]


def test_cover_letter_doc_structure():
    """Verify CoverLetterDoc schema fields."""
    cl = CoverLetterDoc(
        letter_id="cl_001",
        job_id="job_001",
        company="Anthropic Partner",
        title="AI Engineer",
        salutation="Dear Hiring Manager,",
        opening="I am writing to express my strong enthusiasm for the AI Engineer role.",
        body_paragraphs=[
            "With practical experience building LLM and RAG pipelines, I have delivered automation workflows.",
            "My background in B.Tech AI & Data Science provides strong fundamentals in machine learning.",
        ],
        closing="I look forward to discussing how my skills can contribute to your team.",
        sign_off="Sincerely,",
        applicant_name="Ankita Yadav",
        is_approved=False,
    )
    assert cl.is_approved is False
    assert len(cl.body_paragraphs) == 2


def test_application_package_assembly():
    """Verify ApplicationPackage properly binds job, match, resume, cover letter, and answers."""
    job = JobRecord(
        job_id="job_pkg_1",
        company="AI Labs",
        title="Solutions Engineer",
        job_url="https://ailabs.example/careers/1",
        source="searxng",
        date_found="2026-09-29T10:00:00Z",
    )
    match = MatchResult(
        job_id="job_pkg_1",
        match_score=0.85,
        match_status=MatchStatus.STRONG_MATCH,
    )
    resume = ResumeDoc(
        variant="default",
        full_name="Ankita Yadav",
        contact_email="ankita@example.com",
        location="Mumbai, India",
        summary="AI Engineer",
    )
    answers = [
        ApplicationAnswer(
            field_label="Full Name",
            answer_value="Ankita Yadav",
            answer_source="profile",
            is_required=True,
        ),
        ApplicationAnswer(
            field_label="Authorized to work in India",
            answer_value="Yes",
            answer_source="user_verified",
            is_required=True,
        ),
    ]

    pkg = ApplicationPackage(
        application_id="app_12345",
        job=job,
        match=match,
        resume=resume,
        answers=answers,
        user_approved=False,
    )
    assert pkg.job.company == "AI Labs"
    assert pkg.user_approved is False
    assert len(pkg.answers) == 2


def test_safety_assert_no_needs_user_input():
    """Verify that unresolved required fields raise SafetyViolation."""
    valid_answers = [
        ApplicationAnswer(field_label="Name", answer_value="Ankita", is_required=True, answer_source="profile"),
        ApplicationAnswer(field_label="Website", answer_value="NEEDS_USER_INPUT", is_required=False, answer_source="profile"),
    ]
    # Should not raise because Website is not required
    assert_no_needs_user_input_in_required_fields(valid_answers)

    invalid_answers = [
        ApplicationAnswer(field_label="Years of Python", answer_value="NEEDS_USER_INPUT", is_required=True, answer_source="needs_user_input"),
    ]
    with pytest.raises(SafetyViolation, match="unresolved"):
        assert_no_needs_user_input_in_required_fields(invalid_answers)


def test_safety_assert_no_legal_auto_answer():
    """Verify sensitive legal questions require user_verified source."""
    # Sensitive field with user_verified should pass
    assert_no_legal_auto_answer("Are you legally authorized to work?", "user_verified")

    # Sensitive field with generated or profile source must fail
    with pytest.raises(SafetyViolation, match="requires 'user_verified' source"):
        assert_no_legal_auto_answer("Are you legally authorized to work in Germany?", "generated")

    with pytest.raises(SafetyViolation, match="requires 'user_verified' source"):
        assert_no_legal_auto_answer("Do you have a criminal background / felony?", "profile")


def test_safety_assert_optimizer_no_new_claims():
    """Verify resume optimizer cannot introduce unverified skills."""
    original = ResumeDoc(
        full_name="Ankita Yadav",
        contact_email="a@example.com",
        location="Mumbai",
        summary="AI",
        skills={"programming": ["Python", "SQL"]},
    )
    valid_optimized = ResumeDoc(
        full_name="Ankita Yadav",
        contact_email="a@example.com",
        location="Mumbai",
        summary="AI",
        skills={"programming": ["Python", "SQL"]},  # Reordered or same
    )
    # Should pass
    assert_optimizer_no_new_claims(original, valid_optimized)

    fraudulent_optimized = ResumeDoc(
        full_name="Ankita Yadav",
        contact_email="a@example.com",
        location="Mumbai",
        summary="AI",
        skills={"programming": ["Python", "SQL", "Rust", "Kubernetes"]},  # Fabricated new skills
    )
    with pytest.raises(SafetyViolation, match="introduced new ungrounded skills"):
        assert_optimizer_no_new_claims(original, fraudulent_optimized)


def test_safety_assert_user_approved():
    """Verify submission is blocked if user_approved is false."""
    mock_db = MagicMock()
    app_unapproved = MagicMock()
    app_unapproved.user_approved = False
    mock_db.get_application.return_value = app_unapproved

    with pytest.raises(SafetyViolation, match="not user-approved"):
        assert_user_approved("app_1", mock_db)

    app_approved = MagicMock()
    app_approved.user_approved = True
    mock_db.get_application.return_value = app_approved
    # Should succeed without exception
    assert_user_approved("app_2", mock_db)


def test_plugin_registry_and_pipeline_stage():
    """Verify PluginRegistry decorator registration and retrieval."""
    @PluginRegistry.register_source("mock_source")
    class MockSource(PipelineStage):
        stage_name = "mock_discovery"
        async def run(self, input_data):
            return ["job1", "job2"]

    registered_class = PluginRegistry.get_source("mock_source")
    assert registered_class is MockSource
    assert "mock_source" in PluginRegistry.list_sources()


def test_feature_flags():
    """Verify feature flag query from settings.yaml."""
    # From settings.yaml: discovery=on, resume_optimizer=off
    assert is_enabled("discovery") is True
    assert is_enabled("resume_optimizer") is False
    assert is_enabled("non_existent_module") is False
