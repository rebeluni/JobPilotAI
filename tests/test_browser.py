"""
Tests for JobPilot AI Browser Automation & Submission Gate.
Verifies ATS field mapping, challenge/handoff detection, form filling plan,
pre-submission review rendering, and mandatory user approval gate.
"""

import pytest
from jobpilot.applications.resume_master import ResumeMaster
from jobpilot.browser.field_mapper import FieldMapper
from jobpilot.browser.form_filler import FormFiller
from jobpilot.browser.handoff_manager import HandoffManager
from jobpilot.browser.review_screen import ReviewScreen
from jobpilot.browser.submission_gate import SubmissionGate
from jobpilot.core.safety import SafetyViolation
from jobpilot.core.schemas import (
    ApplicationAnswer,
    ApplicationPackage,
    JobRecord,
    MatchResult,
    MatchStatus,
)


def create_sample_package() -> ApplicationPackage:
    master = ResumeMaster()
    resume = master.assemble_resume()
    job = JobRecord(
        job_id="job_browser_001",
        company="Cohere AI",
        title="AI Research Engineer",
        location="Toronto, Canada",
        country="Canada",
        description="Looking for an AI engineer to develop LLMs.",
        skills=["Python", "LLMs"],
        job_url="https://cohere.com/careers/1",
        source="test",
        date_found="2026-09-29",
    )
    match = MatchResult(
        job_id=job.job_id,
        match_score=0.85,
        match_status=MatchStatus.STRONG_MATCH,
        pros=["Strong Python and LLM skills"],
    )
    return ApplicationPackage(
        application_id="app_b_001",
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
            ApplicationAnswer(
                field_label="Years of Experience in PyTorch",
                answer_value="NEEDS_USER_INPUT",
                answer_source="needs_user_input",
                is_required=True,
            ),
        ],
        user_approved=False,
        qa_passed=False,
    )


class TestFieldMapper:
    def test_greenhouse_field_mapping(self):
        mapper = FieldMapper()
        inputs = [
            {"name": "first_name", "id": "first_name", "label": "First Name", "type": "text", "required": True},
            {"name": "last_name", "id": "last_name", "label": "Last Name", "type": "text", "required": True},
            {"name": "email", "id": "email", "label": "Email Address", "type": "email", "required": True},
            {"name": "phone", "id": "phone", "label": "Phone Number", "type": "tel", "required": False},
            {"name": "resume", "id": "resume", "label": "Attach Resume", "type": "file", "required": True},
            {"name": "cover_letter", "id": "cover_letter", "label": "Attach Cover Letter", "type": "file", "required": False},
        ]
        mapped = mapper.map_form_fields(inputs)
        roles = [m.semantic_role for m in mapped]

        assert roles == [
            "first_name",
            "last_name",
            "email",
            "phone",
            "resume_file",
            "cover_letter_file",
        ]

    def test_lever_field_mapping(self):
        mapper = FieldMapper()
        inputs = [
            {"name": "name", "label": "Full Name", "type": "text"},
            {"name": "email", "label": "Email", "type": "email"},
            {"name": "resume", "label": "Resume/CV", "type": "file"},
            {"name": "urls[LinkedIn]", "label": "LinkedIn Profile", "type": "text"},
        ]
        mapped = mapper.map_form_fields(inputs)
        roles = [m.semantic_role for m in mapped]

        assert roles == ["full_name", "email", "resume_file", "linkedin"]


class TestHandoffManager:
    def test_detect_cloudflare_turnstile(self):
        mgr = HandoffManager()
        html = "<html><body><div id='cf-turnstile' class='cf-turnstile-wrapper'></div></body></html>"
        needs_handoff, reason = mgr.check_for_challenge(html)
        assert needs_handoff is True
        assert "Security challenge" in reason

    def test_detect_recaptcha(self):
        mgr = HandoffManager()
        html = "<html><body><div class='g-recaptcha' data-sitekey='xxx'></div></body></html>"
        needs_handoff, reason = mgr.check_for_challenge(html)
        assert needs_handoff is True
        assert "Security challenge" in reason

    def test_detect_mfa(self):
        mgr = HandoffManager()
        html = "<p>Please enter the verification code sent to your phone</p>"
        needs_handoff, reason = mgr.check_for_challenge(html)
        assert needs_handoff is True
        assert "Two-factor authentication" in reason

    def test_clean_page_no_challenge(self):
        mgr = HandoffManager()
        html = "<html><body><h1>Job Application Form</h1></body></html>"
        needs_handoff, reason = mgr.check_for_challenge(html)
        assert needs_handoff is False
        assert reason is None


class TestFormFiller:
    def test_plan_fill_actions_skips_unresolved_fields(self):
        package = create_sample_package()
        mapper = FieldMapper()
        filler = FormFiller()

        inputs = [
            {"label": "Full Name", "name": "name", "type": "text", "required": True},
            {"label": "Years of Experience in PyTorch", "name": "q1", "type": "text", "required": True},
        ]
        mapped = mapper.map_form_fields(inputs)
        report = filler.plan_fill_actions(mapped, package)

        assert report.total_fields == 2
        assert report.filled_count == 1
        assert report.skipped_count == 1
        # PyTorch question is skipped and flagged as unfilled
        assert "Years of Experience in PyTorch" in report.unfilled_fields


class TestReviewScreen:
    def test_render_cli_summary(self):
        package = create_sample_package()
        summary = ReviewScreen.render_cli_summary(package)

        assert "Cohere AI" in summary
        assert "AI Research Engineer" in summary
        assert "APPROVAL GATE" in summary
        assert "Truth QA Gate" in summary

    def test_render_markdown_summary(self):
        package = create_sample_package()
        md = ReviewScreen.render_markdown_summary(package)
        assert "Cohere AI" in md
        assert "Pre-Submission Review" in md


class TestSubmissionGate:
    def test_reject_unapproved_submission_assertion(self):
        package = create_sample_package()
        gate = SubmissionGate()
        with pytest.raises(SafetyViolation, match="not been approved"):
            gate.verify_approved(package)

    def test_approval_prompt_rejects_wrong_input(self):
        package = create_sample_package()
        gate = SubmissionGate()

        # User types "yes" instead of "SUBMIT"
        result = gate.prompt_for_approval(package, input_func=lambda _: "yes")
        assert result is False
        assert package.user_approved is False

        # User types lowercase "submit"
        result = gate.prompt_for_approval(package, input_func=lambda _: "submit")
        assert result is False
        assert package.user_approved is False

    def test_approval_prompt_accepts_exact_submit(self):
        package = create_sample_package()
        gate = SubmissionGate()

        # User types exact "SUBMIT"
        result = gate.prompt_for_approval(package, input_func=lambda _: "SUBMIT")
        assert result is True
        assert package.user_approved is True
