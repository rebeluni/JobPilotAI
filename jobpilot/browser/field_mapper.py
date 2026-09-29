"""
ATS Form Field Mapper for JobPilot AI.
Detects semantic field meanings from HTML attributes across Greenhouse, Lever, Ashby, and Workday.
Maps form inputs to verified candidate facts or flags them for custom question answering.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class MappedField(BaseModel):
    field_id: Optional[str] = None
    field_name: Optional[str] = None
    field_type: str = "text"
    label: str
    semantic_role: str  # e.g., "first_name", "email", "resume_file", "custom_question"
    is_required: bool = False
    options: List[str] = []


class FieldMapper:
    """Classifies HTML form elements into standardized candidate fields."""

    # Heuristic keywords for identifying fields
    ROLE_PATTERNS = {
        "first_name": [r"\bfirst\s*name\b", r"\bgiven\s*name\b", r"\bfname\b"],
        "last_name": [r"\blast\s*name\b", r"\bsurname\b", r"\bfamily\s*name\b", r"\blname\b"],
        "full_name": [r"\bfull\s*name\b", r"\byour\s*name\b", r"\bcandidate\s*name\b", r"^name$"],
        "email": [r"\be-?mail\b"],
        "phone": [r"\bphone\b", r"\bmobile\b", r"\bcontact\s*number\b", r"\btel\b"],
        "location": [r"\bcity\b", r"\blocation\b", r"\baddress\b"],
        "linkedin": [r"\blinkedin\b"],
        "github": [r"\bgithub\b"],
        "portfolio": [r"\bportfolio\b", r"\bwebsite\b", r"\bpersonal\s*site\b"],
        "resume_file": [r"\bresume\b", r"\bcv\b", r"\bcurriculum\s*vitae\b"],
        "cover_letter_file": [r"\bcover\s*letter\b"],
        "work_authorization": [r"\blegally\s*authorized\b", r"\bwork\s*authorization\b", r"\bright\s*to\s*work\b"],
        "visa_sponsorship": [r"\brequire\s*sponsorship\b", r"\bvisa\s*sponsorship\b"],
    }

    def classify_field(
        self,
        label: str,
        name: Optional[str] = None,
        field_id: Optional[str] = None,
        field_type: str = "text",
        is_required: bool = False,
        options: Optional[List[str]] = None,
    ) -> MappedField:
        """
        Classifies an input field into a semantic role based on label, name, and id.
        """
        search_corpus = f"{label} {name or ''} {field_id or ''}".lower()

        # Check for file inputs first
        if field_type == "file":
            if any(re.search(p, search_corpus) for p in self.ROLE_PATTERNS["resume_file"]):
                return MappedField(
                    field_id=field_id,
                    field_name=name,
                    field_type="file",
                    label=label,
                    semantic_role="resume_file",
                    is_required=is_required,
                )
            if any(re.search(p, search_corpus) for p in self.ROLE_PATTERNS["cover_letter_file"]):
                return MappedField(
                    field_id=field_id,
                    field_name=name,
                    field_type="file",
                    label=label,
                    semantic_role="cover_letter_file",
                    is_required=is_required,
                )
            return MappedField(
                field_id=field_id,
                field_name=name,
                field_type="file",
                label=label,
                semantic_role="resume_file",  # Default file upload to resume
                is_required=is_required,
            )

        # Check all other semantic roles
        for role, patterns in self.ROLE_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, search_corpus):
                    return MappedField(
                        field_id=field_id,
                        field_name=name,
                        field_type=field_type,
                        label=label,
                        semantic_role=role,
                        is_required=is_required,
                        options=options or [],
                    )

        # Fallback to custom question
        return MappedField(
            field_id=field_id,
            field_name=name,
            field_type=field_type,
            label=label,
            semantic_role="custom_question",
            is_required=is_required,
            options=options or [],
        )

    def map_form_fields(self, form_inputs: List[Dict[str, Any]]) -> List[MappedField]:
        """Maps a collection of extracted DOM input elements to semantic fields."""
        mapped = []
        for inp in form_inputs:
            field = self.classify_field(
                label=inp.get("label", inp.get("name", "Unknown")),
                name=inp.get("name"),
                field_id=inp.get("id"),
                field_type=inp.get("type", "text"),
                is_required=bool(inp.get("required", False)),
                options=inp.get("options", []),
            )
            mapped.append(field)
        return mapped
