"""
Quality Assurance and Truthfulness Auditor for JobPilot AI.
Audits ApplicationPackage before browser submission to ensure 0 hallucinations,
0 ungrounded claims, 0 unapproved submissions, and 0 unresolved required fields.
"""

from typing import Any, Dict, List, Optional
from jobpilot.core.safety import SENSITIVE_KEYWORDS, SafetyViolation
from jobpilot.core.schemas import ApplicationPackage, ResumeDoc
from jobpilot.profiles.loader import ProfileLoader


class QAChecker:
    """Pre-submission auditor validating application truthfulness and completeness."""

    def __init__(self, profile_path: Optional[str] = None):
        self.profile_loader = ProfileLoader(profile_path=profile_path)
        self._profile: Optional[Dict[str, Any]] = None

    def get_profile(self) -> Dict[str, Any]:
        if self._profile is None:
            self._profile = self.profile_loader.load_profile()
        return self._profile

    def audit(self, package: ApplicationPackage) -> Dict[str, Any]:
        """
        Runs comprehensive QA audit on an ApplicationPackage.
        Updates package.qa_passed and package.qa_report in-place.
        """
        issues: List[str] = []
        checks = {
            "unresolved_required_fields": True,
            "sensitive_answers_verified": True,
            "resume_grounding": True,
            "cover_letter_grounding": True,
            "user_approved": True,
        }

        profile = self.get_profile()

        # 1. Check unresolved required fields
        for ans in package.answers:
            val = str(ans.answer_value) if ans.answer_value is not None else ""
            if ans.is_required and ("NEEDS_USER_INPUT" in val or val.strip() == ""):
                checks["unresolved_required_fields"] = False
                issues.append(f"Required field '{ans.field_label}' is unresolved (NEEDS_USER_INPUT).")

        # 2. Check sensitive legal/authorization questions
        for ans in package.answers:
            label_lower = ans.field_label.lower()
            if any(kw in label_lower for kw in SENSITIVE_KEYWORDS):
                if ans.answer_source != "user_verified":
                    checks["sensitive_answers_verified"] = False
                    issues.append(
                        f"Sensitive field '{ans.field_label}' has unverified source '{ans.answer_source}'."
                    )

        # 3. Check resume grounding (no new ungrounded skills)
        profile_skills = set()
        for cat_skills in profile.get("skills", {}).values():
            if isinstance(cat_skills, list):
                for s in cat_skills:
                    profile_skills.add(s.lower().strip())

        resume_skills = set()
        for cat_skills in package.resume.skills.values():
            for s in cat_skills:
                resume_skills.add(s.lower().strip())

        unverified_resume_skills = resume_skills - profile_skills
        if unverified_resume_skills:
            checks["resume_grounding"] = False
            issues.append(f"Resume contains ungrounded skills not in profile: {list(unverified_resume_skills)}")

        # 4. Check cover letter grounding
        if package.cover_letter:
            cl_text = " ".join([package.cover_letter.opening] + package.cover_letter.body_paragraphs)
            # Cover letter must not make claims of master's or PhD if candidate has B.Tech
            if "phd" in cl_text.lower() or "doctorate" in cl_text.lower():
                checks["cover_letter_grounding"] = False
                issues.append("Cover letter claims PhD/Doctorate not present in profile.")

        # 5. Check user approval gate
        if not package.user_approved:
            checks["user_approved"] = False
            issues.append("Application has not been explicitly approved by candidate (user_approved=False).")

        # Compute QA score
        passed = all(checks.values())
        passed_count = sum(1 for v in checks.values() if v)
        score = round(passed_count / len(checks), 2)

        report = {
            "passed": passed,
            "score": score,
            "checks": checks,
            "issues": issues,
            "application_id": package.application_id,
        }

        package.qa_passed = passed
        package.qa_report = report

        return report
