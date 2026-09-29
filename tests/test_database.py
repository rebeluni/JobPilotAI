"""
Unit and integration tests for Database Repository and Profile loading (Phase 1).
Tests CRUD operations across all 12 tables and profile fact verification.
"""

import os
import tempfile
import pytest
from jobpilot.database.repository import Repository
from jobpilot.database.models import Job, Company, Application
from jobpilot.core.schemas import JobRecord, VisaEvidence, VisaStatus, ConfidenceLevel
from jobpilot.profiles.loader import ProfileLoader, count_facts_and_unresolved
from jobpilot.profiles.answer_bank import AnswerBank


@pytest.fixture
def temp_repo():
    """Create a temporary in-memory or temp-file SQLite database for testing."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_file = os.path.join(tmpdir, "test_jobpilot.db")
        repo = Repository(f"sqlite:///{db_file}")
        repo.init_db()
        try:
            yield repo
        finally:
            repo.engine.dispose()


def test_jobs_crud(temp_repo):
    """Test insert, get, update, and list operations on jobs table."""
    job_record = JobRecord(
        job_id="job_test_001",
        company="Anthropic AI",
        title="AI Engineer",
        description="Build LLM applications and RAG systems.",
        location="London",
        country="UK",
        remote_policy="HYBRID",
        skills=["Python", "LLMs", "RAG"],
        job_url="https://anthropic.com/careers/ai-eng",
        source="greenhouse",
        date_found="2026-09-29T12:00:00Z",
    )
    # Upsert job
    job = temp_repo.upsert_job(job_record)
    assert job.job_id == "job_test_001"
    assert job.company == "Anthropic AI"

    # Retrieve job
    retrieved = temp_repo.get_job("job_test_001")
    assert retrieved is not None
    assert retrieved.title == "AI Engineer"

    # Update job
    temp_repo.upsert_job({
        "job_id": "job_test_001",
        "company": "Anthropic AI",
        "title": "Senior AI Engineer",
        "match_score": 0.88,
        "status": "SHORTLISTED",
    })
    updated = temp_repo.get_job("job_test_001")
    assert updated.title == "Senior AI Engineer"
    assert updated.match_score == 0.88
    assert updated.status == "SHORTLISTED"

    # List jobs
    jobs_list = temp_repo.list_jobs(status="SHORTLISTED")
    assert len(jobs_list) == 1
    assert jobs_list[0].job_id == "job_test_001"


def test_companies_crud(temp_repo):
    """Test insert and retrieval on companies table."""
    comp = temp_repo.upsert_company({
        "company_id": "comp_openai",
        "name": "OpenAI",
        "domain": "openai.com",
        "country": "USA",
        "greenhouse_board": "openai",
        "known_sponsor": 1,
    })
    assert comp.name == "OpenAI"

    retrieved = temp_repo.get_company("comp_openai")
    assert retrieved is not None
    assert retrieved.known_sponsor == 1


def test_site_accounts_crud(temp_repo):
    """Test account creation and lookup."""
    acc = temp_repo.upsert_site_account({
        "account_id": "acc_wd_1",
        "site_url": "https://myworkdayjobs.com",
        "site_name": "Workday",
        "username": "ankita@example.com",
        "session_file": "data/sessions/workday_ankita.json",
    })
    assert acc.username == "ankita@example.com"

    by_site = temp_repo.get_site_account_by_site("https://myworkdayjobs.com", "ankita@example.com")
    assert by_site is not None
    assert by_site.account_id == "acc_wd_1"


def test_applications_and_answers_crud(temp_repo):
    """Test application lifecycle, answers, and events."""
    # First create job
    temp_repo.upsert_job({
        "job_id": "job_app_test",
        "company": "Test Co",
        "title": "Data Analyst",
        "job_url": "https://example.com/job/2",
        "source": "lever",
        "date_found": "2026-09-29T12:00:00Z",
    })

    app = temp_repo.create_application({
        "application_id": "app_001",
        "job_id": "job_app_test",
        "status": "DRAFT",
        "resume_version": "ai_engineer_v1",
        "platform": "ats_greenhouse",
    })
    assert app.status == "DRAFT"
    assert app.user_approved == 0

    # Add answer
    ans = temp_repo.save_application_answer({
        "answer_id": "ans_001",
        "application_id": "app_001",
        "field_label": "Work Authorization",
        "answer_value": "Yes (India)",
        "answer_source": "user_verified",
        "is_verified": 1,
    })
    assert ans.field_label == "Work Authorization"

    answers = temp_repo.get_application_answers("app_001")
    assert len(answers) == 1

    # Record event
    evt = temp_repo.record_event("app_001", "REVIEWED", {"reviewed_by": "user"})
    assert evt.event_type == "REVIEWED"

    # Update application
    temp_repo.update_application("app_001", {"status": "REVIEW", "user_approved": 1})
    updated_app = temp_repo.get_application("app_001")
    assert updated_app.status == "REVIEW"
    assert updated_app.user_approved == 1


def test_visa_evidence_crud(temp_repo):
    """Test saving and retrieving visa evidence."""
    ve = VisaEvidence(
        country="Germany",
        visa_status=VisaStatus.SPONSORSHIP_POSSIBLE,
        route="EU Blue Card",
        confidence=ConfidenceLevel.MEDIUM,
        threshold_met=True,
        threshold_details={"salary": 50000},
        sponsor_status="Known",
    )
    saved = temp_repo.save_visa_evidence(ve)
    assert saved.country == "Germany"

    # Save with job_id
    saved_with_job = temp_repo.save_visa_evidence({
        "evidence_id": "ev_job_1",
        "job_id": "job_1",
        "country": "UK",
        "classification": "SPONSORSHIP_LIKELY",
    })
    records = temp_repo.get_visa_evidence_for_job("job_1")
    assert len(records) == 1
    assert records[0].country == "UK"


def test_user_profile_table_crud(temp_repo):
    """Test user_profile key-value store."""
    temp_repo.set_profile_fact("full_name", "Ankita Yadav", is_verified=1)
    temp_repo.set_profile_fact("experience_years", "1", is_verified=1)

    fact = temp_repo.get_profile_fact("full_name")
    assert fact is not None
    assert fact.value == "Ankita Yadav"

    all_facts = temp_repo.get_all_profile_facts()
    assert all_facts["full_name"] == "Ankita Yadav"
    assert all_facts["experience_years"] == "1"


def test_resume_versions_and_cover_letters_crud(temp_repo):
    """Test resume_versions and cover_letters tables."""
    rv = temp_repo.save_resume_version({
        "version_id": "rv_001",
        "variant": "ai_engineer",
        "file_path": "data/resumes/ankita_ai_eng.pdf",
        "format": "pdf",
        "version_number": 1,
        "is_active": 1,
    })
    assert rv.variant == "ai_engineer"

    active = temp_repo.get_active_resume_version("ai_engineer")
    assert active is not None
    assert active.version_id == "rv_001"

    cl = temp_repo.save_cover_letter({
        "letter_id": "cl_001",
        "content": "Dear Hiring Team...",
        "format": "pdf",
        "is_approved": 0,
    })
    assert cl.letter_id == "cl_001"
    retrieved_cl = temp_repo.get_cover_letter("cl_001")
    assert retrieved_cl.content == "Dear Hiring Team..."


def test_search_runs_and_match_feedback_crud(temp_repo):
    """Test search_runs and match_feedback tables."""
    sr = temp_repo.create_search_run({
        "run_id": "run_001",
        "status": "RUNNING",
    })
    assert sr.run_id == "run_001"

    finished = temp_repo.finish_search_run("run_001", {
        "status": "COMPLETED",
        "query_count": 12,
        "jobs_found": 45,
        "jobs_new": 30,
        "jobs_duplicate": 15,
    })
    assert finished.status == "COMPLETED"
    assert finished.jobs_new == 30

    fb = temp_repo.save_feedback("job_1", "THUMBS_UP", {"role_relevance": 0.05})
    assert fb.feedback == "THUMBS_UP"


def test_profile_loader_and_unresolved_detection():
    """Verify profile loading and count of verified facts vs NEEDS_USER_INPUT."""
    loader = ProfileLoader()
    summary = loader.get_audit_summary()
    assert summary["verified_facts_count"] > 0
    assert summary["needs_user_input_count"] > 0
    assert len(summary["unresolved_fields"]) > 0

    personal = loader.get_personal()
    assert personal["full_name"] == "Ankita Yadav"
    assert personal["location_city"] == "Mumbai"
    assert personal["email"] in ("rebank2125@gmail.com", "NEEDS_USER_INPUT")
    assert personal["linkedin_url"] == "NEEDS_USER_INPUT"

    skills = loader.get_skills()
    assert "Python" in skills["programming"]
    assert "LLMs" in skills["ai_ml"]


def test_answer_bank_matching():
    """Verify AnswerBank maps questions and preserves NEEDS_USER_INPUT safety."""
    ab = AnswerBank()
    summary = ab.get_audit_summary()
    assert summary["verified_entries"] > 0
    assert summary["needs_user_input_entries"] > 0

    # India work authorization should return verified answer
    ans_val, ans_src = ab.match_question("Are you legally authorized to work in India?", country="India")
    assert "authorized to work in India" in ans_val
    assert ans_src == "user_verified"

    # International work authorization must return needs_user_input
    ans_val, ans_src = ab.match_question("Do you require visa sponsorship in Germany?", country="Germany")
    assert "NEEDS_USER_INPUT" in ans_val
    assert ans_src == "needs_user_input"

    # Python experience must return needs_user_input because it hasn't been verified by candidate yet
    ans_val, ans_src = ab.match_question("How many years of Python experience do you have?")
    assert "NEEDS_USER_INPUT" in ans_val
    assert ans_src == "needs_user_input"

    # Highest education is known from degree
    ans_val, ans_src = ab.match_question("What is your highest education degree?")
    assert "Artificial Intelligence & Data Science" in ans_val
    assert ans_src == "user_verified"
