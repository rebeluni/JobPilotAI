"""
Pre-Submission Review Screen for JobPilot AI.
Generates comprehensive inspection summaries before any application can be submitted.
Presents matched answers, document paths, QA check results, and unresolved questions.
"""

from typing import Optional
from jobpilot.browser.form_filler import FillReport
from jobpilot.core.schemas import ApplicationPackage


class ReviewScreen:
    """Renders human-readable inspection summaries before submission."""

    @staticmethod
    def render_cli_summary(
        package: ApplicationPackage,
        fill_report: Optional[FillReport] = None,
    ) -> str:
        """Generates ASCII-formatted terminal review summary."""
        lines = []
        border = "=" * 70
        sub_border = "-" * 70

        lines.append(border)
        lines.append(" JOBPILOT AI — PRE-SUBMISSION APPLICATION REVIEW")
        lines.append(border)

        # Job Info
        lines.append(f"Target Role:    {package.job.title}")
        lines.append(f"Target Company: {package.job.company}")
        lines.append(f"Location:       {package.job.location} ({package.job.country or 'Unknown'})")
        lines.append(f"Application URL:{package.job.job_url}")
        lines.append(sub_border)

        # Match Info
        lines.append(f"Match Score:    {package.match.match_score * 100:.1f}% ({package.match.match_status.value})")
        if package.match.concerns:
            lines.append(f"Concerns Flag:  {', '.join(package.match.concerns)}")
        lines.append(sub_border)

        # Document Info
        lines.append(f"Resume Variant: {package.resume.variant} (Mode: {package.resume.optimizer_mode.value})")
        if package.cover_letter:
            lines.append(f"Cover Letter:   Generated (Approved: {package.cover_letter.is_approved})")
        lines.append(sub_border)

        # QA Status
        qa_status = "PASSED [OK]" if package.qa_passed else "FAILED / PENDING [!]"
        lines.append(f"Truth QA Gate:  {qa_status}")
        if package.qa_report and package.qa_report.get("issues"):
            for issue in package.qa_report["issues"]:
                lines.append(f"  - ISSUE: {issue}")
        lines.append(sub_border)

        # Fill Status
        if fill_report:
            lines.append(f"Form Fields:    {fill_report.filled_count}/{fill_report.total_fields} filled automatically.")
            if fill_report.unfilled_fields:
                lines.append(f"UNFILLED FIELDS (Candidate Input Required):")
                for u in fill_report.unfilled_fields:
                    lines.append(f"  * {u}")
            lines.append(sub_border)

        # Mandatory Approval Banner
        lines.append(" APPROVAL GATE: The system NEVER clicks 'Submit' automatically.")
        lines.append(" Explicit confirmation is required to proceed.")
        lines.append(border)

        return "\n".join(lines)

    @staticmethod
    def render_markdown_summary(
        package: ApplicationPackage,
        fill_report: Optional[FillReport] = None,
    ) -> str:
        """Generates Markdown formatted summary for Web Dashboard / UI."""
        md = []
        md.append(f"## Pre-Submission Review: {package.job.title} at {package.job.company}")
        md.append(f"- **Match Score:** {package.match.match_score * 100:.1f}% (`{package.match.match_status.value}`)")
        md.append(f"- **Resume Variant:** `{package.resume.variant}`")
        md.append(f"- **QA Gate:** {'Passed' if package.qa_passed else 'Requires Review'}")

        if fill_report and fill_report.unfilled_fields:
            md.append("### Unresolved Fields")
            for f in fill_report.unfilled_fields:
                md.append(f"- ⚠️ **{f}** (Needs User Input)")

        return "\n".join(md)
