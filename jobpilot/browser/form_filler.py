"""
Playwright Form Filler for JobPilot AI.
Safely populates ATS application forms using verified candidate package data.
Uploads generated PDF/DOCX resumes and cover letters.
Skips any field marked NEEDS_USER_INPUT for human-in-the-loop completion.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from jobpilot.browser.field_mapper import FieldMapper, MappedField
from jobpilot.core.schemas import ApplicationAnswer, ApplicationPackage

logger = logging.getLogger(__name__)


class FillAction(BaseModel):
    field_label: str
    semantic_role: str
    action_type: str  # "fill_text", "upload_file", "select_option", "skipped"
    value_preview: str
    success: bool
    notes: Optional[str] = None


class FillReport(BaseModel):
    total_fields: int
    filled_count: int
    skipped_count: int
    actions: List[FillAction] = []
    unfilled_fields: List[str] = []


class FormFiller:
    """Populates ATS form fields in Playwright browser sessions."""

    def __init__(self):
        self.field_mapper = FieldMapper()

    def determine_field_value(
        self,
        mapped_field: MappedField,
        package: ApplicationPackage,
        resume_file_path: Optional[Path] = None,
        cover_letter_file_path: Optional[Path] = None,
    ) -> Optional[Any]:
        """Resolves the verified value for a mapped field from the application package."""
        role = mapped_field.semantic_role

        if role == "first_name":
            return package.resume.full_name.split()[0]
        elif role == "last_name":
            parts = package.resume.full_name.split()
            return parts[-1] if len(parts) > 1 else ""
        elif role == "full_name":
            return package.resume.full_name
        elif role == "email":
            email = package.resume.contact_email
            return email if email != "NEEDS_USER_INPUT" else None
        elif role == "phone":
            phone = package.resume.contact_phone
            return phone if phone != "NEEDS_USER_INPUT" else None
        elif role == "location":
            return package.resume.location
        elif role == "resume_file":
            return str(resume_file_path) if resume_file_path and resume_file_path.exists() else None
        elif role == "cover_letter_file":
            return str(cover_letter_file_path) if cover_letter_file_path and cover_letter_file_path.exists() else None

        # Look in package answers
        for ans in package.answers:
            if ans.field_label.lower() in mapped_field.label.lower() or mapped_field.label.lower() in ans.field_label.lower():
                val = str(ans.answer_value) if ans.answer_value is not None else ""
                if "NEEDS_USER_INPUT" in val or val.strip() == "":
                    return None
                return val

        return None

    def plan_fill_actions(
        self,
        mapped_fields: List[MappedField],
        package: ApplicationPackage,
        resume_file_path: Optional[Path] = None,
        cover_letter_file_path: Optional[Path] = None,
    ) -> FillReport:
        """
        Creates a structured plan of fill actions, identifying what will be populated
        and what must be left for human input.
        """
        actions: List[FillAction] = []
        filled = 0
        skipped = 0
        unfilled: List[str] = []

        for f in mapped_fields:
            val = self.determine_field_value(f, package, resume_file_path, cover_letter_file_path)

            if val is not None and str(val).strip() != "":
                action_type = "upload_file" if f.field_type == "file" else "fill_text"
                preview = str(val)[:30] + "..." if len(str(val)) > 30 else str(val)
                actions.append(FillAction(
                    field_label=f.label,
                    semantic_role=f.semantic_role,
                    action_type=action_type,
                    value_preview=preview,
                    success=True,
                ))
                filled += 1
            else:
                actions.append(FillAction(
                    field_label=f.label,
                    semantic_role=f.semantic_role,
                    action_type="skipped",
                    value_preview="[NEEDS_USER_INPUT]",
                    success=False,
                    notes="Requires candidate input or file not provided",
                ))
                skipped += 1
                if f.is_required:
                    unfilled.append(f.label)

        return FillReport(
            total_fields=len(mapped_fields),
            filled_count=filled,
            skipped_count=skipped,
            actions=actions,
            unfilled_fields=unfilled,
        )

    async def execute_fill_on_page(
        self,
        page: Any,
        mapped_fields: List[MappedField],
        package: ApplicationPackage,
        resume_file_path: Optional[Path] = None,
        cover_letter_file_path: Optional[Path] = None,
    ) -> FillReport:
        """
        Executes filling on a live Playwright page.
        """
        report = self.plan_fill_actions(mapped_fields, package, resume_file_path, cover_letter_file_path)

        for action in report.actions:
            if not action.success:
                continue

            # In live page filling, match element by label or id
            try:
                if action.action_type == "upload_file":
                    file_input = await page.query_selector(f"input[type='file']")
                    if file_input:
                        await file_input.set_input_files(action.value_preview)
                else:
                    selector = f"input[name='{action.field_label}'], textarea[name='{action.field_label}']"
                    elem = await page.query_selector(selector)
                    if elem:
                        await elem.fill(action.value_preview)
            except Exception as e:
                logger.warning(f"Could not fill {action.field_label}: {e}")

        return report
