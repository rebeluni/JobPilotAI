"""
Shared Pydantic Schemas for JobPilot AI.
All inter-module communication is strictly constrained to these contract types.
No module may import another module's internal classes.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class RemotePolicy(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNKNOWN = "UNKNOWN"


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    UNKNOWN = "UNKNOWN"


class VisaStatus(str, Enum):
    INDIA = "INDIA"                                   # Domestic citizen rights, no sponsorship
    SPONSORSHIP_LIKELY = "SPONSORSHIP_LIKELY"         # Known sponsor or verified relocation
    SPONSORSHIP_POSSIBLE = "SPONSORSHIP_POSSIBLE"     # Qualified role meets criteria, needs confirmation
    SPONSORSHIP_UNLIKELY = "SPONSORSHIP_UNLIKELY"     # Role / salary below threshold or no sponsor history
    NOT_SUITABLE = "NOT_SUITABLE"                     # Explicitly excludes foreign applicants
    UNCLEAR = "UNCLEAR"                               # Insufficient data, manual review needed


class MatchStatus(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"     # >= 0.80
    GOOD_MATCH = "GOOD_MATCH"         # 0.65 - 0.79
    STRETCH_MATCH = "STRETCH_MATCH"   # 0.50 - 0.64
    POOR_MATCH = "POOR_MATCH"         # 0.35 - 0.49
    NO_MATCH = "NO_MATCH"             # < 0.35 or hard filter failure


class OptimizerMode(str, Enum):
    OFF = "off"
    SUGGEST = "suggest"
    AUTO = "auto"


class RoleTier(str, Enum):
    EXACT = "EXACT"
    ADJACENT = "ADJACENT"
    STRETCH = "STRETCH"


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class JobRecord(BaseModel):
    """
    Contract schema for normalized job postings.
    Output of extraction/discovery; input to matching, immigration, and application modules.
    """
    job_id: str
    company: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    remote_policy: RemotePolicy = RemotePolicy.UNKNOWN
    employment_type: EmploymentType = EmploymentType.UNKNOWN
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    skills: list[str] = Field(default_factory=list)
    role_family: Optional[str] = None
    role_tier: Optional[RoleTier] = RoleTier.EXACT
    job_url: str
    source: str
    date_posted: Optional[str] = None
    date_found: str
    is_expired: bool = False
    is_ghost_job: bool = False
    quality_score: Optional[float] = 1.0

    # Immigration fields
    visa_status: Optional[VisaStatus] = VisaStatus.UNCLEAR
    visa_evidence: Optional[dict[str, Any]] = None
    immigration_route: Optional[str] = None
    sponsor_verified: bool = False
    relocation_support: bool = False
    international_applicant_signal: Optional[str] = None
    work_authorization_requirement: Optional[str] = None

    # Matching & Embeddings
    embedding_vector: Optional[list[float]] = None
    match_score: Optional[float] = None
    match_status: Optional[MatchStatus] = None
    match_reasoning: Optional[dict[str, Any]] = None
    recommended_resume: Optional[str] = None
    application_priority: Optional[str] = None

    # Status tracking
    status: str = "NEW"
    user_feedback: Optional[str] = None
    is_duplicate: bool = False


class MatchResult(BaseModel):
    """
    Contract schema for job matching evaluations.
    Output of matching engine; input to application preparation and dashboard shortlist.
    """
    job_id: str
    match_score: float = Field(ge=0.0, le=1.0)
    match_status: MatchStatus
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    recommended_variant: str = "default"
    optimizer_recommended: bool = False
    reasoning: str = ""


class VisaEvidence(BaseModel):
    """
    Contract schema for immigration viability assessments.
    Output of immigration classifier; stored in visa_evidence table.
    """
    country: str
    visa_status: VisaStatus
    route: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    threshold_met: Optional[bool] = None
    threshold_details: dict[str, Any] = Field(default_factory=dict)
    sponsor_status: Optional[str] = None
    disclaimer: str = "This assessment is for informational planning only and does not constitute legal immigration advice."
    evidence_snippets: list[str] = Field(default_factory=list)
    verified_rule: bool = False


class ResumeBullet(BaseModel):
    text: str
    skills_demonstrated: list[str] = Field(default_factory=list)
    impact_level: str = "HIGH"


class ResumeDoc(BaseModel):
    """
    Contract schema for structured resume documents.
    Output of resume loader/optimizer; input to document renderers (PDF/DOCX).
    """
    variant: str = "default"
    full_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    location: str
    summary: str
    skills: dict[str, list[str]] = Field(default_factory=dict)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    source_variant: str = "master"
    optimizer_mode: OptimizerMode = OptimizerMode.OFF
    optimizer_diff: list[str] = Field(default_factory=list)


class CoverLetterDoc(BaseModel):
    """
    Contract schema for tailored cover letters.
    """
    letter_id: str
    job_id: str
    company: str
    title: str
    salutation: str
    opening: str
    body_paragraphs: list[str] = Field(default_factory=list)
    closing: str
    sign_off: str
    applicant_name: str
    is_approved: bool = False


class ApplicationAnswer(BaseModel):
    """
    Contract schema for a single form question answer.
    """
    field_id: Optional[str] = None
    field_label: str
    field_type: str = "text"
    answer_value: Any
    answer_source: str  # "profile", "user_verified", "generated", "needs_user_input"
    is_required: bool = False
    confidence: float = 1.0
    flagged_for_review: bool = False


class ApplicationPackage(BaseModel):
    """
    Complete package passed to the browser automation agent.
    Combines verified job details, matching output, documents, and form answers.
    """
    application_id: str
    job: JobRecord
    match: MatchResult
    resume: ResumeDoc
    cover_letter: Optional[CoverLetterDoc] = None
    answers: list[ApplicationAnswer] = Field(default_factory=list)
    user_approved: bool = False
    qa_passed: bool = False
    qa_report: Optional[dict[str, Any]] = None


class RoleExpansion(BaseModel):
    """
    Contract schema for expanded job titles from RoleExpander.
    """
    role_families: list[str]
    exact_titles: list[str] = Field(default_factory=list)
    adjacent_titles: list[str] = Field(default_factory=list)
    stretch_titles: list[str] = Field(default_factory=list)
    approved: bool = False
    pending_review: bool = True


class MatchInput(BaseModel):
    """
    Contract schema for input to the matching engine.
    """
    job: JobRecord
    profile_summary: str
    visa_status: Optional[VisaStatus] = VisaStatus.UNCLEAR
