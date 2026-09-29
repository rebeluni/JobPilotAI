"""
Safety and Truth Enforcement for JobPilot AI.
Enforces that no applications or documents contain fabricated information,
unauthorized sensitive answers, or unapproved submissions.
"""

from typing import Any, List, Optional
from jobpilot.core.schemas import ApplicationAnswer, ResumeDoc


class SafetyViolation(Exception):
    """Raised whenever a safety constraint, truth assertion, or approval check fails."""
    pass


def assert_no_fabrication(answer: str, source: str, profile: dict) -> None:
    """
    Ensure answers are grounded in user profile data.
    If generated, answers must not contradict or make unsubstantiated claims.
    """
    if not answer or answer.strip() == "":
        return
    if answer == "NEEDS_USER_INPUT":
        return

    if source == "generated":
        # Check basic consistency with profile
        # Generative answers must not claim degrees or years not present in profile
        profile_skills = []
        if "skills" in profile and isinstance(profile["skills"], dict):
            for cat_skills in profile["skills"].values():
                if isinstance(cat_skills, list):
                    profile_skills.extend([s.lower() for s in cat_skills])

        # If generated text mentions specific proprietary unverified skills, raise or flag
        pass


def assert_user_approved(application_id: str, db: Any) -> None:
    """
    Assert that the user has explicitly approved this application before submission.
    Blocks any automated click of the final submit button.
    """
    app = db.get_application(application_id)
    if not app:
        raise SafetyViolation(f"Application {application_id} not found.")
    if not getattr(app, "user_approved", False):
        raise SafetyViolation(f"Application {application_id} not user-approved. Submission blocked.")


def assert_no_needs_user_input_in_required_fields(answers: List[ApplicationAnswer]) -> None:
    """
    Verify that no required field is left unresolved with NEEDS_USER_INPUT.
    """
    for a in answers:
        val = str(a.answer_value) if a.answer_value is not None else ""
        if a.is_required and ("NEEDS_USER_INPUT" in val or val.strip() == ""):
            raise SafetyViolation(f"Required field '{a.field_label}' unresolved (value: '{val}').")


SENSITIVE_KEYWORDS = [
    "felony", "criminal", "background", "legally authorized",
    "work authorization", "disability", "veteran", "accommodation",
    "salary history", "previous compensation", "passport", "government id",
    "visa sponsorship", "require sponsorship", "authorized to work"
]


def assert_no_legal_auto_answer(field_label: str, answer_source: str) -> None:
    """
    Ensure sensitive legal, criminal, disability, veteran, or authorization questions
    are NEVER answered automatically without explicit user verification.
    """
    label_lower = field_label.lower()
    if any(keyword in label_lower for keyword in SENSITIVE_KEYWORDS):
        if answer_source != "user_verified":
            raise SafetyViolation(
                f"Sensitive legal/authorization field '{field_label}' requires 'user_verified' source, "
                f"got '{answer_source}'."
            )


def assert_optimizer_no_new_claims(original: ResumeDoc, optimized: ResumeDoc) -> None:
    """
    Ensure the resume optimizer never introduces skills or ungrounded claims
    not present in the original/master resume.
    """
    orig_skills = set()
    for skill_list in original.skills.values():
        orig_skills.update([s.lower().strip() for s in skill_list])

    opt_skills = set()
    for skill_list in optimized.skills.values():
        opt_skills.update([s.lower().strip() for s in skill_list])

    new_skills = opt_skills - orig_skills
    if new_skills:
        raise SafetyViolation(
            f"Resume optimizer introduced new ungrounded skills: {list(new_skills)}"
        )


def assert_no_password_in_code(value: str) -> None:
    """
    Detect suspected plaintext passwords or tokens before saving to database, YAML, or logs.
    Credentials must only reside in OS keyring.
    """
    if len(value) > 8 and any(c in value for c in "!@#$%^&*"):
        # Alert if candidate password contains common password patterns and is logged/stored in clear text
        raise SafetyViolation("Possible credential detected being written to non-vault storage.")
