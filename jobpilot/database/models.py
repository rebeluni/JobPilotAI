"""
SQLAlchemy ORM models for all 12 JobPilot AI tables.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat()


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String(128), primary_key=True)
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    remote_policy = Column(String(50), default="UNKNOWN")
    employment_type = Column(String(50), default="UNKNOWN")
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    experience_min = Column(Integer, nullable=True)
    experience_max = Column(Integer, nullable=True)
    skills = Column(Text, nullable=True)  # JSON array
    role_family = Column(String(100), nullable=True)
    role_tier = Column(String(50), default="EXACT")
    job_url = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    date_posted = Column(String(50), nullable=True)
    date_found = Column(String(50), nullable=False, default=utcnow_str)
    is_expired = Column(Integer, default=0)
    is_ghost_job = Column(Integer, default=0)
    quality_score = Column(Float, default=1.0)

    # Immigration fields
    visa_status = Column(String(50), default="UNCLEAR")
    visa_evidence = Column(Text, nullable=True)  # JSON blob
    immigration_route = Column(String(255), nullable=True)
    sponsor_verified = Column(Integer, default=0)
    relocation_support = Column(Integer, default=0)
    international_applicant_signal = Column(Text, nullable=True)
    work_authorization_requirement = Column(Text, nullable=True)

    # Matching & Embeddings
    embedding_vector = Column(Text, nullable=True)  # JSON float array
    match_score = Column(Float, nullable=True)
    match_status = Column(String(50), nullable=True)
    match_reasoning = Column(Text, nullable=True)  # JSON blob
    recommended_resume = Column(String(100), nullable=True)
    application_priority = Column(String(50), nullable=True)

    # Status tracking
    status = Column(String(50), default="NEW")
    user_feedback = Column(String(50), nullable=True)
    is_duplicate = Column(Integer, default=0)
    created_at = Column(String(50), nullable=False, default=utcnow_str)
    updated_at = Column(String(50), nullable=False, default=utcnow_str, onupdate=utcnow_str)

    applications = relationship("Application", back_populates="job")
    visa_evidences = relationship("VisaEvidenceModel", back_populates="job")
    feedbacks = relationship("MatchFeedback", back_populates="job")


class Company(Base):
    __tablename__ = "companies"

    company_id = Column(String(128), primary_key=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    greenhouse_board = Column(String(255), nullable=True)
    lever_site = Column(String(255), nullable=True)
    ashby_board = Column(String(255), nullable=True)
    career_page_url = Column(Text, nullable=True)
    known_sponsor = Column(Integer, default=0)
    sponsor_evidence = Column(Text, nullable=True)  # JSON
    created_at = Column(String(50), nullable=False, default=utcnow_str)
    updated_at = Column(String(50), nullable=False, default=utcnow_str, onupdate=utcnow_str)

    visa_evidences = relationship("VisaEvidenceModel", back_populates="company")


class SiteAccount(Base):
    __tablename__ = "site_accounts"

    account_id = Column(String(128), primary_key=True)
    site_url = Column(String(255), nullable=False)
    site_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    # Password stored in OS keyring (keyring library) under key: jobpilot:{site_url}:{username}
    # NEVER stored in database
    session_file = Column(Text, nullable=True)  # Path to Playwright storage_state JSON
    created_at = Column(String(50), nullable=False, default=utcnow_str)
    last_used_at = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    applications = relationship("Application", back_populates="account")


class Application(Base):
    __tablename__ = "applications"

    application_id = Column(String(128), primary_key=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=False)
    account_id = Column(String(128), ForeignKey("site_accounts.account_id"), nullable=True)
    status = Column(String(50), default="DRAFT")  # DRAFT/REVIEW/SUBMITTED/REJECTED/INTERVIEW/OFFER
    resume_version = Column(String(100), nullable=True)
    resume_optimized = Column(Integer, default=0)
    optimizer_mode = Column(String(20), default="OFF")  # OFF/SUGGEST/AUTO
    cover_letter_id = Column(String(128), nullable=True)
    applied_at = Column(String(50), nullable=True)
    platform = Column(String(100), nullable=True)  # ats_greenhouse/lever/workday/direct/email
    application_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    user_approved = Column(Integer, default=0)  # MUST be 1 before any submission
    qa_passed = Column(Integer, default=0)
    qa_report = Column(Text, nullable=True)  # JSON
    audit_screenshot = Column(Text, nullable=True)  # Path to screenshot taken at submission
    audit_form_data = Column(Text, nullable=True)  # JSON snapshot of form values at submission
    created_at = Column(String(50), nullable=False, default=utcnow_str)
    updated_at = Column(String(50), nullable=False, default=utcnow_str, onupdate=utcnow_str)

    job = relationship("Job", back_populates="applications")
    account = relationship("SiteAccount", back_populates="applications")
    answers = relationship("ApplicationAnswerModel", back_populates="application")
    events = relationship("ApplicationEvent", back_populates="application")


class ApplicationAnswerModel(Base):
    __tablename__ = "application_answers"

    answer_id = Column(String(128), primary_key=True)
    application_id = Column(String(128), ForeignKey("applications.application_id"), nullable=False)
    field_label = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=True)
    answer_value = Column(Text, nullable=True)
    answer_source = Column(String(50), nullable=True)  # user_profile/answer_bank/generated/needs_user_input/user_verified
    is_verified = Column(Integer, default=0)
    created_at = Column(String(50), nullable=False, default=utcnow_str)

    application = relationship("Application", back_populates="answers")


class VisaEvidenceModel(Base):
    __tablename__ = "visa_evidence"

    evidence_id = Column(String(128), primary_key=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=True)
    company_id = Column(String(128), ForeignKey("companies.company_id"), nullable=True)
    country = Column(String(100), nullable=False)
    evidence_type = Column(String(50), nullable=True)  # job_posting/government_source/employer_profile/inferred
    source_url = Column(Text, nullable=True)
    source_date = Column(String(50), nullable=True)
    content_snippet = Column(Text, nullable=True)
    confidence = Column(String(20), nullable=True)  # HIGH/MEDIUM/LOW
    classification = Column(String(50), nullable=True)
    disclaimer = Column(Text, default="Informational only. Not legal immigration advice.")
    created_at = Column(String(50), nullable=False, default=utcnow_str)

    job = relationship("Job", back_populates="visa_evidences")
    company = relationship("Company", back_populates="visa_evidences")


class UserProfile(Base):
    __tablename__ = "user_profile"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(50), nullable=True)
    is_verified = Column(Integer, default=1)
    last_updated = Column(String(50), nullable=False, default=utcnow_str)


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    version_id = Column(String(128), primary_key=True)
    variant = Column(String(100), nullable=False)
    file_path = Column(Text, nullable=False)
    format = Column(String(20), nullable=False)  # docx/pdf/txt
    version_number = Column(Integer, default=1)
    is_active = Column(Integer, default=1)
    optimizer_mode = Column(String(20), default="OFF")  # OFF/SUGGEST/AUTO
    notes = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False, default=utcnow_str)


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    letter_id = Column(String(128), primary_key=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=True)
    application_id = Column(String(128), ForeignKey("applications.application_id"), nullable=True)
    content = Column(Text, nullable=False)
    file_path = Column(Text, nullable=True)
    format = Column(String(20), nullable=True)
    is_approved = Column(Integer, default=0)
    created_at = Column(String(50), nullable=False, default=utcnow_str)


class SearchRun(Base):
    __tablename__ = "search_runs"

    run_id = Column(String(128), primary_key=True)
    started_at = Column(String(50), nullable=False, default=utcnow_str)
    completed_at = Column(String(50), nullable=True)
    query_count = Column(Integer, default=0)
    jobs_found = Column(Integer, default=0)
    jobs_new = Column(Integer, default=0)
    jobs_duplicate = Column(Integer, default=0)
    status = Column(String(50), default="RUNNING")
    error_message = Column(Text, nullable=True)
    config_snapshot = Column(Text, nullable=True)  # JSON


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    event_id = Column(String(128), primary_key=True)
    application_id = Column(String(128), ForeignKey("applications.application_id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # CREATED/REVIEWED/SUBMITTED/EMAIL_RECEIVED/STATUS_CHANGE/FOLLOW_UP
    event_data = Column(Text, nullable=True)  # JSON
    created_at = Column(String(50), nullable=False, default=utcnow_str)

    application = relationship("Application", back_populates="events")

    def __init__(self, **kwargs):
        if "details" in kwargs and "event_data" not in kwargs:
            kwargs["event_data"] = kwargs.pop("details")
        super().__init__(**kwargs)

    @property
    def details(self):
        return self.event_data

    @details.setter
    def details(self, value):
        self.event_data = value


class MatchFeedback(Base):
    __tablename__ = "match_feedback"

    feedback_id = Column(String(128), primary_key=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=False)
    feedback = Column(String(50), nullable=False)  # THUMBS_UP/THUMBS_DOWN
    weight_delta = Column(Text, nullable=True)  # JSON
    created_at = Column(String(50), nullable=False, default=utcnow_str)

    job = relationship("Job", back_populates="feedbacks")
