"""
Application Follow-Up Manager for JobPilot AI.
Calculates follow-up deadlines (5-7 business days post-submission) and
generates polite, professional follow-up email drafts.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from jobpilot.database.models import Application, Job
from jobpilot.database.repository import Repository


def calculate_follow_up_date(applied_date_str: str, business_days: int = 5) -> str:
    """
    Calculates follow-up date by adding business days (skipping weekends).
    Format of applied_date_str: YYYY-MM-DD or ISO timestamp.
    """
    try:
        # Extract date portion
        date_part = applied_date_str.split("T")[0].split()[0]
        current_date = datetime.strptime(date_part, "%Y-%m-%d")
    except Exception:
        current_date = datetime.utcnow()

    added_days = 0
    while added_days < business_days:
        current_date += timedelta(days=1)
        # 0 = Monday, 4 = Friday, 5 = Saturday, 6 = Sunday
        if current_date.weekday() < 5:
            added_days += 1

    return current_date.strftime("%Y-%m-%d")


def generate_follow_up_email(
    company: str,
    role_title: str,
    applied_date: str,
    candidate_name: str = "Ankita Yadav",
) -> Dict[str, str]:
    """
    Generates a polite follow-up inquiry referencing genuine technical competencies.
    """
    subject = f"Following up on application for {role_title} - {candidate_name}"

    body = (
        f"Dear {company} Recruiting Team,\n\n"
        f"I hope this message finds you well.\n\n"
        f"I am writing to politely follow up on my application for the {role_title} position, "
        f"which I submitted on {applied_date}. I remain very enthusiastic about the opportunity "
        f"to contribute my expertise in Artificial Intelligence, Python, and intelligent workflow automation to {company}.\n\n"
        f"Please let me know if there are any additional details, portfolio projects, or references I can provide "
        f"to assist with your evaluation.\n\n"
        f"Thank you for your time and consideration, and I look forward to hearing from you.\n\n"
        f"Warm regards,\n\n"
        f"{candidate_name}\n"
        f"Mumbai, India"
    )

    return {
        "subject": subject,
        "body": body,
    }


class FollowUpManager:
    """Tracks submission deadlines and identifies pending follow-ups."""

    def __init__(self, repo: Repository):
        self.repo = repo

    def get_pending_follow_ups(self, days_threshold: int = 7) -> List[Dict[str, Any]]:
        """
        Retrieves submitted applications that have had no status change after days_threshold days.
        """
        now = datetime.utcnow()
        cutoff_date = (now - timedelta(days=days_threshold)).strftime("%Y-%m-%d")

        results = []
        with self.repo.session_scope() as session:
            apps = (
                session.query(Application, Job)
                .join(Job, Application.job_id == Job.job_id)
                .filter(Application.status == "SUBMITTED")
                .all()
            )

            for app, job in apps:
                applied_at = app.applied_at or app.created_at
                if applied_at and applied_at[:10] <= cutoff_date:
                    follow_up_due = calculate_follow_up_date(applied_at, business_days=5)
                    email_draft = generate_follow_up_email(
                        company=job.company,
                        role_title=job.title,
                        applied_date=applied_at[:10],
                    )
                    results.append({
                        "application_id": app.application_id,
                        "job_id": job.job_id,
                        "company": job.company,
                        "title": job.title,
                        "applied_at": applied_at,
                        "follow_up_due": follow_up_due,
                        "email_draft": email_draft,
                    })

        return results
