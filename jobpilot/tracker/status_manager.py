"""
Application Status State Machine for JobPilot AI.
Enforces valid lifecycle transitions and ensures every state change is audited.
"""

from typing import Dict, List, Optional, Set
from jobpilot.core.schemas import ApplicationStatus
from jobpilot.database.models import Application, utcnow_str
from jobpilot.database.repository import Repository

VALID_TRANSITIONS: Dict[str, Set[str]] = {
    "DRAFT": {"REVIEW"},
    "REVIEW": {"DRAFT", "SUBMITTED"},
    "SUBMITTED": {"INTERVIEW", "REJECTED"},
    "INTERVIEW": {"INTERVIEW", "OFFER", "REJECTED"},
    "OFFER": {"ACCEPTED", "DECLINED"},
    "REJECTED": set(),
    "ACCEPTED": set(),
    "DECLINED": set(),
}


class InvalidStateTransition(Exception):
    """Raised when an illegal application lifecycle transition is attempted."""
    pass


class StatusManager:
    """Manages application status state transitions and audit records."""

    def __init__(self, repo: Repository):
        self.repo = repo

    def update_status(
        self,
        application_id: str,
        new_status: str,
        note: Optional[str] = None,
    ) -> Application:
        """
        Transitions an application to a new status.
        Validates transition rules and records an audit event in SQLite.
        """
        new_status_norm = new_status.upper().strip()

        with self.repo.session_scope() as session:
            app = session.query(Application).filter(Application.application_id == application_id).first()
            if not app:
                raise ValueError(f"Application {application_id} not found.")

            current = (app.status or "DRAFT").upper()
            allowed = VALID_TRANSITIONS.get(current, set())

            if new_status_norm not in allowed:
                raise InvalidStateTransition(
                    f"Invalid status transition for application {application_id}: "
                    f"'{current}' -> '{new_status_norm}'. Allowed next states: {list(allowed)}"
                )

            # Special invariant: cannot transition to SUBMITTED without user_approved == 1
            if new_status_norm == "SUBMITTED" and not app.user_approved:
                raise InvalidStateTransition(
                    f"Cannot transition application {application_id} to SUBMITTED: "
                    f"Explicit user approval has not been granted (user_approved=0)."
                )

            old_status = app.status
            app.status = new_status_norm
            if new_status_norm == "SUBMITTED" and not app.applied_at:
                app.applied_at = utcnow_str()

            # Record audit event
            from jobpilot.database.models import ApplicationEvent
            import uuid
            event_id = f"evt_{application_id}_{uuid.uuid4().hex[:10]}"
            event = ApplicationEvent(
                event_id=event_id,
                application_id=application_id,
                event_type="STATUS_CHANGED",
                event_data=f"Status changed from {old_status} to {new_status_norm}. Note: {note or 'None'}",
                created_at=utcnow_str(),
            )
            session.add(event)

            return app
