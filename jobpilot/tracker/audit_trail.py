"""
Audit Trail Logger for JobPilot AI.
Provides an immutable record of all system events, status changes,
question answering lookups, and candidate approvals in the local SQLite database.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid
from jobpilot.database.models import ApplicationEvent, utcnow_str
from jobpilot.database.repository import Repository, get_data_dir


def get_default_audit_dir() -> Path:
    p = get_data_dir() / "audit"
    p.mkdir(parents=True, exist_ok=True)
    return p


class AuditTrail:
    """Records and queries immutable lifecycle events for job applications."""

    def __init__(self, repo: Repository):
        self.repo = repo

    def log_event(
        self,
        application_id: str,
        event_type: str,
        details: Union[Dict[str, Any], str],
    ) -> ApplicationEvent:
        """Records a new event in the database."""
        event_id = f"evt_{application_id}_{uuid.uuid4().hex[:10]}"
        details_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details)

        with self.repo.session_scope() as session:
            event = ApplicationEvent(
                event_id=event_id,
                application_id=application_id,
                event_type=event_type.upper(),
                event_data=details_str,
                created_at=utcnow_str(),
            )
            session.add(event)
            return event

    def get_events_for_application(self, application_id: str) -> List[Dict[str, Any]]:
        """Retrieves chronological event history for an application."""
        with self.repo.session_scope() as session:
            events = (
                session.query(ApplicationEvent)
                .filter(ApplicationEvent.application_id == application_id)
                .order_by(ApplicationEvent.created_at.asc())
                .all()
            )
            results = []
            for e in events:
                results.append({
                    "event_id": e.event_id,
                    "application_id": e.application_id,
                    "event_type": e.event_type,
                    "details": e.event_data,
                    "created_at": e.created_at,
                })
            return results

    def export_audit_log(self, application_id: Optional[str] = None, output_file: Optional[Path] = None) -> Path:
        """Exports audit events to a JSON file in the audit folder."""
        out_path = output_file or (get_default_audit_dir() / f"audit_{application_id or 'all'}.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with self.repo.session_scope() as session:
            query = session.query(ApplicationEvent)
            if application_id:
                query = query.filter(ApplicationEvent.application_id == application_id)
            events = query.order_by(ApplicationEvent.created_at.asc()).all()

            data = [
                {
                    "event_id": e.event_id,
                    "application_id": e.application_id,
                    "event_type": e.event_type,
                    "details": e.details,
                    "created_at": e.created_at,
                }
                for e in events
            ]

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return out_path
