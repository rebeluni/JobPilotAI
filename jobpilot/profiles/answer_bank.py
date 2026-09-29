"""
Answer Bank Loader and Matcher for Job Application Form Fields.
Matches form questions to canonical answers while enforcing that any unverified
or unresolved answer remains flagged as NEEDS_USER_INPUT.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import yaml
from jobpilot.profiles.loader import count_facts_and_unresolved


def get_default_answer_bank_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "jobpilot" / "profiles" / "answer_bank.yaml"


class AnswerBank:
    """Manages application question-to-answer mappings."""

    def __init__(self, yaml_path: Optional[str] = None):
        self.yaml_path = Path(yaml_path) if yaml_path else get_default_answer_bank_path()
        self._data: Optional[Dict[str, Any]] = None

    def load(self, reload: bool = False) -> Dict[str, Any]:
        if self._data is not None and not reload:
            return self._data
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"Answer bank not found at {self.yaml_path}")
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}
        return self._data

    def get_audit_summary(self) -> Dict[str, Any]:
        data = self.load()
        verified, needs_input, unresolved = count_facts_and_unresolved(data)
        return {
            "path": str(self.yaml_path),
            "verified_entries": verified,
            "needs_user_input_entries": needs_input,
            "unresolved_keys": unresolved,
        }

    def match_question(self, question_text: str, country: Optional[str] = None) -> Tuple[Optional[str], str]:
        """
        Match question text to an answer bank entry.
        Returns: (answer_value, answer_source)
        Source can be 'answer_bank', 'user_verified', or 'needs_user_input'.
        """
        data = self.load()
        q_lower = question_text.lower()

        # Work authorization and sponsorship checks
        if any(w in q_lower for w in [
            "authorized to work", "legally authorized", "work authorization",
            "right to work", "sponsorship", "visa sponsorship", "require sponsorship"
        ]):
            if country and country.lower() == "india":
                val = data.get("work_authorization", {}).get("india_answer")
                return (val, "user_verified")
            else:
                val = data.get("work_authorization", {}).get("international_answer")
                return (val, "needs_user_input")

        # Years of experience checks
        years_data = data.get("years_of_experience", {})
        if "year" in q_lower or "experience" in q_lower:
            for skill, val in years_data.items():
                if skill.replace("_", " ") in q_lower:
                    if "NEEDS_USER_INPUT" in str(val):
                        return (str(val), "needs_user_input")
                    return (str(val), "user_verified")

        # Notice period
        if "notice period" in q_lower or "notice" in q_lower:
            val = data.get("notice_period")
            return (str(val), "needs_user_input" if "NEEDS_USER_INPUT" in str(val) else "user_verified")

        # Salary expectations
        if "salary" in q_lower or "compensation" in q_lower:
            if "inr" in q_lower or "₹" in q_lower or "lpa" in q_lower:
                val = data.get("salary_expectation_inr")
                return (str(val), "needs_user_input" if "NEEDS_USER_INPUT" in str(val) else "user_verified")
            else:
                val = data.get("salary_expectation_usd")
                return (str(val), "needs_user_input" if "NEEDS_USER_INPUT" in str(val) else "user_verified")

        # Highest education
        if any(w in q_lower for w in ["highest education", "highest degree", "degree level"]):
            val = data.get("highest_education")
            return (str(val), "user_verified")

        # Relocation
        if "relocate" in q_lower or "relocation" in q_lower:
            val = data.get("willing_to_relocate")
            return (str(val), "needs_user_input" if "NEEDS_USER_INPUT" in str(val) else "user_verified")

        return (None, "unknown")
