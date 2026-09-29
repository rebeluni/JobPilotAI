"""
Tests for JobPilot AI Application Preparation & Resume Optimizer.
Verifies resume master loading, optimizer modes (OFF, SUGGEST, AUTO),
truthfulness enforcement, cover letter generation, answer engine lookup, and QA auditing.
"""

import pytest
from jobpilot.applications.answer_engine import AnswerEngine
from jobpilot.applications.cover_letter_gen import CoverLetterGenerator
from jobpilot.applications.qa_checker import QAChecker
from jobpilot.applications.resume_master import ResumeMaster
from jobpilot.applications.resume_optimizer import ResumeOptimizer
from jobpilot.core.safety import SafetyViolation, assert_optimizer_no_new_claims
from jobpilot.core.schemas import (
    ApplicationAnswer,
    ApplicationPackage,
    JobRecord,
    MatchResult,
    MatchStatus,
    OptimizerMode,
    ResumeDoc,
)


def create_sample_job() -> JobRecord:
    return JobRecord(
        job_id="job_app_test_01",
        company="Anthropic AI",
        title="AI Engineer - LLMs & Agents",
        location="Remote",
        country="India",
        description="We are looking for an AI Engineer with Python, LLMs, RAG, and AI Agents experience.",
        skills=["Python", "LLMs", "RAG", "AI Agents", "Docker"],
        job_url="https://anthropic.com/jobs/1",
        source="test",
        date_found="2026-09-29",
    )


class TestResumeMaster:
    def test_assemble_master_resume(self):
        master = ResumeMaster()
        resume = master.assemble_resume(variant="default")
        assert resume.full_name == "Ankita Yadav"
        assert "Mumbai" in resume.location
        assert "programming" in resume.skills
        assert "Python" in resume.skills["programming"]
        assert resume.optimizer_mode == OptimizerMode.OFF

    def test_assemble_variants(self):
        master = ResumeMaster()
        ai_resume = master.assemble_resume(variant="ai_engineer")
        assert list(ai_resume.skills.keys())[0] == "ai_ml"

        auto_resume = master.assemble_resume(variant="ai_automation")
        assert list(auto_resume.skills.keys())[0] == "platforms_tools"


class TestResumeOptimizer:
    def test_optimizer_mode_off(self):
        master = ResumeMaster()
        resume = master.assemble_resume()
        job = create_sample_job()

        optimizer = ResumeOptimizer(mode=OptimizerMode.OFF)
        opt_resume = optimizer.optimize(resume, job)

        assert opt_resume.optimizer_mode == OptimizerMode.OFF
        assert opt_resume.optimizer_diff == []
        assert opt_resume.skills == resume.skills

    def test_optimizer_mode_suggest(self):
        master = ResumeMaster()
        resume = master.assemble_resume()
        job = create_sample_job()

        optimizer = ResumeOptimizer(mode=OptimizerMode.SUGGEST)
        opt_resume = optimizer.optimize(resume, job)

        assert opt_resume.optimizer_mode == OptimizerMode.SUGGEST
        assert len(opt_resume.optimizer_diff) > 0
        assert any("SUGGESTION" in d for d in opt_resume.optimizer_diff)
        # Content remains untouched in SUGGEST mode
        assert opt_resume.skills == resume.skills

    def test_optimizer_mode_auto_reorders_matching_skills(self):
        master = ResumeMaster()
        resume = master.assemble_resume()
        job = create_sample_job()

        optimizer = ResumeOptimizer(mode=OptimizerMode.AUTO)
        opt_resume = optimizer.optimize(resume, job)

        assert opt_resume.optimizer_mode == OptimizerMode.AUTO
        assert len(opt_resume.optimizer_diff) > 0
        # Check that matching skills like Python and LLMs are moved to front of their lists
        assert opt_resume.skills["programming"][0] == "Python"
        assert opt_resume.skills["ai_ml"][0] in ("LLMs", "RAG", "AI Agents")

        # Crucial safety check: zero new ungrounded skills
        assert_optimizer_no_new_claims(resume, opt_resume)

    def test_optimizer_safety_violation_on_hallucinated_skill(self):
        master = ResumeMaster()
        resume = master.assemble_resume()
        fake_resume = master.assemble_resume()
        # Injected fake skill
        fake_resume.skills["programming"].append("Rust")

        with pytest.raises(SafetyViolation, match="ungrounded skills"):
            assert_optimizer_no_new_claims(resume, fake_resume)


class TestCoverLetterGenerator:
    def test_generate_cover_letter(self):
        gen = CoverLetterGenerator()
        job = create_sample_job()
        cl = gen.generate(job)

        assert cl.job_id == job.job_id
        assert cl.company == "Anthropic AI"
        assert "Ankita Yadav" in cl.applicant_name
        assert "Anthropic AI" in cl.salutation
        assert "Artificial Intelligence & Data Science" in cl.opening
        assert len(cl.body_paragraphs) >= 2
        # Human-in-the-loop review enforced
        assert cl.is_approved is False


class TestAnswerEngine:
    def test_answer_profile_fields(self):
        engine = AnswerEngine()
        name_ans = engine.answer_question("Full Name")
        assert name_ans.answer_value == "Ankita Yadav"
        assert name_ans.answer_source == "profile"

        city_ans = engine.answer_question("Current City")
        assert city_ans.answer_value == "Mumbai"
        assert city_ans.answer_source == "profile"

    def test_sensitive_legal_questions_require_user_input(self):
        engine = AnswerEngine()
        q1 = engine.answer_question("Have you ever been convicted of a felony?")
        assert q1.answer_value == "NEEDS_USER_INPUT"
        assert q1.answer_source == "needs_user_input"
        assert q1.flagged_for_review is True

        q2 = engine.answer_question("Do you have a disability requiring accommodation?")
        assert q2.answer_value == "NEEDS_USER_INPUT"
        assert q2.flagged_for_review is True

    def test_work_authorization_india_vs_international(self):
        engine = AnswerEngine()
        ans_india = engine.answer_question("Are you legally authorized to work?", country="India")
        assert ans_india.answer_source == "user_verified"

        ans_intl = engine.answer_question("Are you legally authorized to work?", country="UK")
        assert ans_intl.answer_source == "needs_user_input"


class TestQAChecker:
    def test_qa_checker_audit_workflow(self):
        master = ResumeMaster()
        resume = master.assemble_resume()
        job = create_sample_job()
        match = MatchResult(
            job_id=job.job_id,
            match_score=0.88,
            match_status=MatchStatus.STRONG_MATCH,
        )

        package = ApplicationPackage(
            application_id="app_qa_001",
            job=job,
            match=match,
            resume=resume,
            answers=[
                ApplicationAnswer(
                    field_label="Full Name",
                    answer_value="Ankita Yadav",
                    answer_source="profile",
                    is_required=True,
                ),
                ApplicationAnswer(
                    field_label="Email",
                    answer_value="ankita@example.com",
                    answer_source="profile",
                    is_required=True,
                ),
            ],
            user_approved=True,  # Approved by user
        )

        qa = QAChecker()
        report = qa.audit(package)

        assert report["passed"] is True
        assert report["score"] == 1.0
        assert package.qa_passed is True

    def test_qa_checker_blocks_unapproved_or_incomplete_package(self):
        master = ResumeMaster()
        resume = master.assemble_resume()
        job = create_sample_job()
        match = MatchResult(job_id=job.job_id, match_score=0.75, match_status=MatchStatus.GOOD_MATCH)

        package = ApplicationPackage(
            application_id="app_qa_002",
            job=job,
            match=match,
            resume=resume,
            answers=[
                ApplicationAnswer(
                    field_label="Phone Number",
                    answer_value="NEEDS_USER_INPUT",
                    answer_source="needs_user_input",
                    is_required=True,  # Required but unresolved!
                ),
            ],
            user_approved=False,  # Not approved!
        )

        qa = QAChecker()
        report = qa.audit(package)

        assert report["passed"] is False
        assert package.qa_passed is False
        assert any("NEEDS_USER_INPUT" in issue for issue in report["issues"])
        assert any("user_approved=False" in issue for issue in report["issues"])
