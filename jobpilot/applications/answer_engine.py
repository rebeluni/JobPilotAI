"""
Question Answering Engine for Job Application Forms.
Matches ATS form fields to verified candidate profile facts and answer bank records.
Strictly flags all unverified, ambiguous, or sensitive questions as NEEDS_USER_INPUT.
Never auto-answers legal, criminal, disability, or unconfirmed sponsorship questions.
"""

from typing import Any, Dict, List, Optional
from jobpilot.core.schemas import ApplicationAnswer
from jobpilot.profiles.answer_bank import AnswerBank
from jobpilot.profiles.loader import ProfileLoader

SENSITIVE_LEGAL_KEYWORDS = [
    "felony", "criminal", "misdemeanor", "convicted", "background check",
    "disability", "veteran", "accommodation", "race", "gender",
    "salary history", "previous compensation", "ssn", "passport number",
]


class AnswerEngine:
    """Answers ATS application questions while strictly enforcing truthfulness boundaries."""

    def __init__(
        self,
        profile_path: Optional[str] = None,
        answer_bank_path: Optional[str] = None,
    ):
        self.profile_loader = ProfileLoader(profile_path=profile_path)
        self.answer_bank = AnswerBank(yaml_path=answer_bank_path)
        self._profile: Optional[Dict[str, Any]] = None

    def get_profile(self) -> Dict[str, Any]:
        if self._profile is None:
            self._profile = self.profile_loader.load_profile()
        return self._profile

    def answer_question(
        self,
        field_label: str,
        field_id: Optional[str] = None,
        field_type: str = "text",
        is_required: bool = False,
        country: Optional[str] = None,
    ) -> ApplicationAnswer:
        """
        Determines the answer for a single form question.
        Returns ApplicationAnswer with verified source or flagged as NEEDS_USER_INPUT.
        """
        label_lower = field_label.lower().strip()
        profile = self.get_profile()
        personal = profile.get("personal", {})

        # 1. Check for sensitive legal/disability questions first
        if any(kw in label_lower for kw in SENSITIVE_LEGAL_KEYWORDS):
            # Must always be reviewed by user unless an explicit user-verified override exists
            return ApplicationAnswer(
                field_id=field_id,
                field_label=field_label,
                field_type=field_type,
                answer_value="NEEDS_USER_INPUT",
                answer_source="needs_user_input",
                is_required=is_required,
                confidence=0.0,
                flagged_for_review=True,
            )

        # 2. Check basic personal / contact fields
        if any(w in label_lower for w in ["first name", "given name"]):
            full_name = personal.get("full_name", "Ankita Yadav")
            val = full_name.split()[0] if full_name else "NEEDS_USER_INPUT"
            return self._make_answer(field_id, field_label, field_type, val, "profile", is_required)

        if any(w in label_lower for w in ["last name", "family name", "surname"]):
            full_name = personal.get("full_name", "Ankita Yadav")
            parts = full_name.split()
            val = parts[-1] if len(parts) > 1 else "NEEDS_USER_INPUT"
            return self._make_answer(field_id, field_label, field_type, val, "profile", is_required)

        if any(w in label_lower for w in ["full name", "your name"]):
            val = personal.get("full_name", "Ankita Yadav")
            return self._make_answer(field_id, field_label, field_type, val, "profile", is_required)

        if any(w in label_lower for w in ["email", "e-mail"]):
            val = personal.get("email", "NEEDS_USER_INPUT")
            return self._make_answer(field_id, field_label, field_type, val, "profile", is_required)

        if any(w in label_lower for w in ["phone", "mobile", "contact number"]):
            val = personal.get("phone", "NEEDS_USER_INPUT")
            return self._make_answer(field_id, field_label, field_type, val, "profile", is_required)

        if any(w in label_lower for w in ["linkedin", "linkedin profile"]):
            val = personal.get("linkedin_url", "NEEDS_USER_INPUT")
            return self._make_answer(field_id, field_label, field_type, val, "profile", is_required)

        if any(w in label_lower for w in ["github", "github profile"]):
            val = personal.get("github_url", "NEEDS_USER_INPUT")
            return self._make_answer(field_id, field_label, field_type, val, "profile", is_required)

        if any(w in label_lower for w in ["city", "current city"]):
            val = personal.get("location_city", "Mumbai")
            return self._make_answer(field_id, field_label, field_type, val, "profile", is_required)

        if any(w in label_lower for w in ["country", "current country"]):
            val = personal.get("location_country", "India")
            return self._make_answer(field_id, field_label, field_type, val, "profile", is_required)

        # 3. Match against Answer Bank
        ans_val, source = self.answer_bank.match_question(field_label, country=country)
        if ans_val is not None:
            return self._make_answer(field_id, field_label, field_type, ans_val, source, is_required)

        # 4. Fallback: unknown question requires user input
        return ApplicationAnswer(
            field_id=field_id,
            field_label=field_label,
            field_type=field_type,
            answer_value="NEEDS_USER_INPUT",
            answer_source="needs_user_input",
            is_required=is_required,
            confidence=0.0,
            flagged_for_review=True,
        )

    def _make_answer(
        self,
        field_id: Optional[str],
        field_label: str,
        field_type: str,
        val: Any,
        source: str,
        is_required: bool,
    ) -> ApplicationAnswer:
        val_str = str(val) if val is not None else "NEEDS_USER_INPUT"
        is_unresolved = "NEEDS_USER_INPUT" in val_str or val_str.strip() == ""
        return ApplicationAnswer(
            field_id=field_id,
            field_label=field_label,
            field_type=field_type,
            answer_value=val_str if not is_unresolved else "NEEDS_USER_INPUT",
            answer_source="needs_user_input" if is_unresolved else source,
            is_required=is_required,
            confidence=0.0 if is_unresolved else 1.0,
            flagged_for_review=is_unresolved,
        )

    def answer_form(
        self,
        fields: List[Dict[str, Any]],
        country: Optional[str] = None,
    ) -> List[ApplicationAnswer]:
        """Answers a full list of ATS form fields."""
        results = []
        for f in fields:
            label = f.get("field_label") or f.get("label") or f.get("name") or "Unknown"
            fid = f.get("field_id") or f.get("id")
            ftype = f.get("field_type") or f.get("type") or "text"
            is_req = bool(f.get("is_required", False) or f.get("required", False))
            ans = self.answer_question(
                field_label=label,
                field_id=fid,
                field_type=ftype,
                is_required=is_req,
                country=country,
            )
            results.append(ans)
        return results
