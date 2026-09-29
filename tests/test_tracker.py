"""
Tests for JobPilot AI Tracker & Feedback Loop.
Verifies status lifecycle state machine, audit event logging, follow-up deadlines, and email generation.
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
import pytest

from jobpilot.database.models import Application, Job, utcnow_str
from jobpilot.database.repository import Repository
from jobpilot.tracker.audit_trail import AuditTrail
from jobpilot.tracker.follow_ups import (
    FollowUpManager,
    calculate_follow_up_date,
    generate_follow_up_email,
)
from jobpilot.tracker.status_manager import InvalidStateTransition, StatusManager


@pytest.fixture
def temp_repo(tmp_path):
    db_file = tmp_path / "test_tracker.db"
    db_url = f"sqlite:///{db_file}"
    repo = Repository(db_url=db_url)
    repo.init_db()
    try:
        yield repo
    finally:
        repo.engine.dispose()


@pytest.fixture
def sample_job_and_app(temp_repo):
    job_id = "job_tracker_01"
    app_id = "app_tracker_01"

    temp_repo.upsert_job({
        "job_id": job_id,
        "company": "DeepMind",
        "title": "Research Engineer",
        "job_url": "https://deepmind.google/jobs/1",
        "source": "test",
        "date_found": "2026-09-29",
    })

    with temp_repo.session_scope() as session:
        app = Application(
            application_id=app_id,
            job_id=job_id,
            status="DRAFT",
            user_approved=0,
            created_at=utcnow_str(),
        )
        session.add(app)

    return job_id, app_id


class TestStatusManager:
    def test_valid_transitions(self, temp_repo, sample_job_and_app):
        _, app_id = sample_job_and_app
        mgr = StatusManager(temp_repo)

        # 1. DRAFT -> REVIEW
        mgr.update_status(app_id, "REVIEW")
        with temp_repo.session_scope() as session:
            app = session.query(Application).filter(Application.application_id == app_id).first()
            assert app.status == "REVIEW"

        # Mark user_approved before moving to SUBMITTED
        with temp_repo.session_scope() as session:
            app = session.query(Application).filter(Application.application_id == app_id).first()
            app.user_approved = 1

        # 2. REVIEW -> SUBMITTED
        mgr.update_status(app_id, "SUBMITTED")
        with temp_repo.session_scope() as session:
            app = session.query(Application).filter(Application.application_id == app_id).first()
            assert app.status == "SUBMITTED"
            assert app.applied_at is not None

        # 3. SUBMITTED -> INTERVIEW
        mgr.update_status(app_id, "INTERVIEW")
        with temp_repo.session_scope() as session:
            app = session.query(Application).filter(Application.application_id == app_id).first()
            assert app.status == "INTERVIEW"

    def test_blocked_transition_without_user_approval(self, temp_repo, sample_job_and_app):
        _, app_id = sample_job_and_app
        mgr = StatusManager(temp_repo)
        mgr.update_status(app_id, "REVIEW")

        # Try to transition to SUBMITTED while user_approved is 0
        with pytest.raises(InvalidStateTransition, match="approval has not been granted"):
            mgr.update_status(app_id, "SUBMITTED")

    def test_invalid_lifecycle_jump(self, temp_repo, sample_job_and_app):
        _, app_id = sample_job_and_app
        mgr = StatusManager(temp_repo)

        # Cannot jump from DRAFT directly to OFFER
        with pytest.raises(InvalidStateTransition, match="Invalid status transition"):
            mgr.update_status(app_id, "OFFER")


class TestAuditTrail:
    def test_log_and_retrieve_events(self, temp_repo, sample_job_and_app):
        _, app_id = sample_job_and_app
        audit = AuditTrail(temp_repo)

        audit.log_event(app_id, "MATCHED", {"score": 0.89, "variant": "ai_engineer"})
        audit.log_event(app_id, "FORM_FILLED", {"fields_filled": 6, "skipped": 0})

        history = audit.get_events_for_application(app_id)
        assert len(history) == 2
        assert history[0]["event_type"] == "MATCHED"
        assert history[1]["event_type"] == "FORM_FILLED"

    def test_export_audit_log(self, temp_repo, sample_job_and_app, tmp_path):
        _, app_id = sample_job_and_app
        audit = AuditTrail(temp_repo)
        audit.log_event(app_id, "APPROVAL", "User confirmed with SUBMIT")

        export_file = tmp_path / "audit_test.json"
        out = audit.export_audit_log(application_id=app_id, output_file=export_file)

        assert out.exists()
        with open(out, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]["application_id"] == app_id


class TestFollowUps:
    def test_calculate_follow_up_date_skips_weekends(self):
        # A Friday date: 2026-10-02 (Friday)
        # Adding 5 business days: Mon (1), Tue (2), Wed (3), Thu (4), Fri (5) -> 2026-10-09
        applied = "2026-10-02"
        due = calculate_follow_up_date(applied, business_days=5)
        assert due == "2026-10-09"

    def test_generate_follow_up_email(self):
        email = generate_follow_up_email(
            company="DeepMind",
            role_title="Research Engineer",
            applied_date="2026-09-20",
        )
        assert "Research Engineer" in email["subject"]
        assert "DeepMind" in email["body"]
        assert "Ankita Yadav" in email["body"]

    def test_get_pending_follow_ups(self, temp_repo, sample_job_and_app):
        job_id, app_id = sample_job_and_app
        # Make application 10 days old and SUBMITTED
        old_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
        with temp_repo.session_scope() as session:
            app = session.query(Application).filter(Application.application_id == app_id).first()
            app.status = "SUBMITTED"
            app.user_approved = 1
            app.applied_at = old_date

        mgr = FollowUpManager(temp_repo)
        pending = mgr.get_pending_follow_ups(days_threshold=7)

        assert len(pending) == 1
        assert pending[0]["company"] == "DeepMind"
        assert "email_draft" in pending[0]
