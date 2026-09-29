"""
Database Repository and CRUD layer for JobPilot AI.
Manages SQLite connection, sessions, and entity operations across all 12 tables.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import create_engine, select, update, desc
from sqlalchemy.orm import sessionmaker, Session

from jobpilot.database.models import (
    Base,
    Job,
    Company,
    SiteAccount,
    Application,
    ApplicationAnswerModel,
    VisaEvidenceModel,
    UserProfile,
    ResumeVersion,
    CoverLetter,
    SearchRun,
    ApplicationEvent,
    MatchFeedback,
    utcnow_str,
)
from jobpilot.core.schemas import JobRecord, VisaEvidence


def get_default_db_path() -> str:
    """Resolve database path from environment or settings.yaml."""
    env_path = os.environ.get("DB_PATH")
    if env_path:
        return env_path

    # Try config/settings.yaml
    project_root = Path(__file__).resolve().parent.parent.parent
    settings_file = project_root / "config" / "settings.yaml"
    if settings_file.exists():
        try:
            import yaml
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = yaml.safe_load(f) or {}
            data_dir = settings.get("app", {}).get("data_dir")
            if data_dir:
                return str(Path(data_dir) / "jobpilot.db")
        except Exception:
            pass

    # Fallback to local data folder outside OneDrive if possible
    desktop_path = Path.home() / "Desktop" / "JobPilotData"
    if desktop_path.exists():
        return str(desktop_path / "jobpilot.db")
    return str(project_root / "jobpilot.db")


def get_data_dir() -> Path:
    """Return data directory where database and user artifacts are stored."""
    db_path = get_default_db_path()
    return Path(db_path).parent


class Repository:
    """Database repository providing complete CRUD access."""

    def __init__(self, db_url_or_path: Optional[str] = None, db_url: Optional[str] = None):
        target = db_url or db_url_or_path
        if not target:
            db_path = get_default_db_path()
            # Ensure parent folder exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self.db_url = f"sqlite:///{db_path}"
        elif target.startswith("sqlite://"):
            self.db_url = target
        else:
            Path(target).parent.mkdir(parents=True, exist_ok=True)
            self.db_url = f"sqlite:///{target}"

        self.engine = create_engine(self.db_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_db(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Provide a new session context."""
        return self.SessionLocal()

    from contextlib import contextmanager

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------ JOBS ------------------
    def upsert_job(self, job_data: Union[JobRecord, Dict[str, Any]]) -> Job:
        """Insert or update a job posting."""
        if isinstance(job_data, JobRecord):
            data = job_data.model_dump()
        else:
            data = dict(job_data)

        # Convert list/dict fields to JSON strings for SQLite storage
        for field in ["skills", "visa_evidence", "embedding_vector", "match_reasoning"]:
            if field in data and isinstance(data[field], (list, dict)):
                data[field] = json.dumps(data[field])

        job_id = data.get("job_id")
        now = utcnow_str()
        with self.get_session() as session:
            existing = session.query(Job).filter(Job.job_id == job_id).first()
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k) and k != "created_at":
                        setattr(existing, k, v)
                existing.updated_at = now
                session.commit()
                session.refresh(existing)
                return existing
            else:
                if "created_at" not in data or not data["created_at"]:
                    data["created_at"] = now
                if "updated_at" not in data or not data["updated_at"]:
                    data["updated_at"] = now
                new_job = Job(**{k: v for k, v in data.items() if hasattr(Job, k)})
                session.add(new_job)
                session.commit()
                session.refresh(new_job)
                return new_job

    def get_job(self, job_id: str) -> Optional[Job]:
        with self.get_session() as session:
            return session.query(Job).filter(Job.job_id == job_id).first()

    def list_jobs(self, status: Optional[str] = None, limit: int = 100) -> List[Job]:
        with self.get_session() as session:
            query = session.query(Job)
            if status:
                query = query.filter(Job.status == status)
            return query.order_by(desc(Job.created_at)).limit(limit).all()

    # ------------------ COMPANIES ------------------
    def upsert_company(self, company_data: Dict[str, Any]) -> Company:
        data = dict(company_data)
        if "sponsor_evidence" in data and isinstance(data["sponsor_evidence"], (list, dict)):
            data["sponsor_evidence"] = json.dumps(data["sponsor_evidence"])

        company_id = data.get("company_id")
        now = utcnow_str()
        with self.get_session() as session:
            existing = session.query(Company).filter(Company.company_id == company_id).first()
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k) and k != "created_at":
                        setattr(existing, k, v)
                existing.updated_at = now
                session.commit()
                session.refresh(existing)
                return existing
            else:
                if "created_at" not in data or not data["created_at"]:
                    data["created_at"] = now
                if "updated_at" not in data or not data["updated_at"]:
                    data["updated_at"] = now
                new_company = Company(**{k: v for k, v in data.items() if hasattr(Company, k)})
                session.add(new_company)
                session.commit()
                session.refresh(new_company)
                return new_company

    def get_company(self, company_id: str) -> Optional[Company]:
        with self.get_session() as session:
            return session.query(Company).filter(Company.company_id == company_id).first()

    # ------------------ SITE ACCOUNTS ------------------
    def upsert_site_account(self, account_data: Dict[str, Any]) -> SiteAccount:
        data = dict(account_data)
        account_id = data.get("account_id")
        now = utcnow_str()
        with self.get_session() as session:
            existing = session.query(SiteAccount).filter(SiteAccount.account_id == account_id).first()
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k) and k != "created_at":
                        setattr(existing, k, v)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                if "created_at" not in data or not data["created_at"]:
                    data["created_at"] = now
                new_acc = SiteAccount(**{k: v for k, v in data.items() if hasattr(SiteAccount, k)})
                session.add(new_acc)
                session.commit()
                session.refresh(new_acc)
                return new_acc

    def get_site_account(self, account_id: str) -> Optional[SiteAccount]:
        with self.get_session() as session:
            return session.query(SiteAccount).filter(SiteAccount.account_id == account_id).first()

    def get_site_account_by_site(self, site_url: str, username: str) -> Optional[SiteAccount]:
        with self.get_session() as session:
            return session.query(SiteAccount).filter(
                SiteAccount.site_url == site_url,
                SiteAccount.username == username
            ).first()

    # ------------------ APPLICATIONS ------------------
    def create_application(self, app_data: Dict[str, Any]) -> Application:
        data = dict(app_data)
        for field in ["qa_report", "audit_form_data"]:
            if field in data and isinstance(data[field], (list, dict)):
                data[field] = json.dumps(data[field])

        now = utcnow_str()
        if "created_at" not in data or not data["created_at"]:
            data["created_at"] = now
        if "updated_at" not in data or not data["updated_at"]:
            data["updated_at"] = now

        with self.get_session() as session:
            app = Application(**{k: v for k, v in data.items() if hasattr(Application, k)})
            session.add(app)
            session.commit()
            session.refresh(app)
            return app

    def get_application(self, application_id: str) -> Optional[Application]:
        with self.get_session() as session:
            return session.query(Application).filter(Application.application_id == application_id).first()

    def update_application(self, application_id: str, updates: Dict[str, Any]) -> Optional[Application]:
        data = dict(updates)
        for field in ["qa_report", "audit_form_data"]:
            if field in data and isinstance(data[field], (list, dict)):
                data[field] = json.dumps(data[field])

        now = utcnow_str()
        data["updated_at"] = now
        with self.get_session() as session:
            app = session.query(Application).filter(Application.application_id == application_id).first()
            if not app:
                return None
            for k, v in data.items():
                if hasattr(app, k) and k != "created_at":
                    setattr(app, k, v)
            session.commit()
            session.refresh(app)
            return app

    # ------------------ APPLICATION ANSWERS ------------------
    def save_application_answer(self, answer_data: Dict[str, Any]) -> ApplicationAnswerModel:
        data = dict(answer_data)
        if "created_at" not in data or not data["created_at"]:
            data["created_at"] = utcnow_str()
        with self.get_session() as session:
            ans = ApplicationAnswerModel(**{k: v for k, v in data.items() if hasattr(ApplicationAnswerModel, k)})
            session.add(ans)
            session.commit()
            session.refresh(ans)
            return ans

    def get_application_answers(self, application_id: str) -> List[ApplicationAnswerModel]:
        with self.get_session() as session:
            return session.query(ApplicationAnswerModel).filter(
                ApplicationAnswerModel.application_id == application_id
            ).all()

    # ------------------ VISA EVIDENCE ------------------
    def save_visa_evidence(self, evidence_data: Union[VisaEvidence, Dict[str, Any]]) -> VisaEvidenceModel:
        if isinstance(evidence_data, VisaEvidence):
            data = evidence_data.model_dump()
            data["classification"] = str(data.get("visa_status", ""))
            data["confidence"] = str(data.get("confidence", ""))
            data["content_snippet"] = "; ".join(data.get("evidence_snippets", []))
            data["evidence_id"] = data.get("evidence_id") or f"ev_{data.get('country')}_{utcnow_str()}"
        else:
            data = dict(evidence_data)

        if "created_at" not in data or not data["created_at"]:
            data["created_at"] = utcnow_str()

        with self.get_session() as session:
            ev = VisaEvidenceModel(**{k: v for k, v in data.items() if hasattr(VisaEvidenceModel, k)})
            session.add(ev)
            session.commit()
            session.refresh(ev)
            return ev

    def get_visa_evidence_for_job(self, job_id: str) -> List[VisaEvidenceModel]:
        with self.get_session() as session:
            return session.query(VisaEvidenceModel).filter(VisaEvidenceModel.job_id == job_id).all()

    # ------------------ USER PROFILE TABLE ------------------
    def set_profile_fact(self, key: str, value: str, is_verified: int = 1, value_type: str = "string") -> UserProfile:
        now = utcnow_str()
        with self.get_session() as session:
            existing = session.query(UserProfile).filter(UserProfile.key == key).first()
            if existing:
                existing.value = str(value)
                existing.is_verified = is_verified
                existing.value_type = value_type
                existing.last_updated = now
                session.commit()
                session.refresh(existing)
                return existing
            else:
                fact = UserProfile(
                    key=key,
                    value=str(value),
                    value_type=value_type,
                    is_verified=is_verified,
                    last_updated=now,
                )
                session.add(fact)
                session.commit()
                session.refresh(fact)
                return fact

    def get_profile_fact(self, key: str) -> Optional[UserProfile]:
        with self.get_session() as session:
            return session.query(UserProfile).filter(UserProfile.key == key).first()

    def get_all_profile_facts(self) -> Dict[str, Any]:
        with self.get_session() as session:
            records = session.query(UserProfile).all()
            return {r.key: r.value for r in records}

    # ------------------ RESUME VERSIONS ------------------
    def save_resume_version(self, version_data: Dict[str, Any]) -> ResumeVersion:
        data = dict(version_data)
        if "created_at" not in data or not data["created_at"]:
            data["created_at"] = utcnow_str()
        with self.get_session() as session:
            rv = ResumeVersion(**{k: v for k, v in data.items() if hasattr(ResumeVersion, k)})
            session.add(rv)
            session.commit()
            session.refresh(rv)
            return rv

    def get_active_resume_version(self, variant: str) -> Optional[ResumeVersion]:
        with self.get_session() as session:
            return session.query(ResumeVersion).filter(
                ResumeVersion.variant == variant,
                ResumeVersion.is_active == 1
            ).order_by(desc(ResumeVersion.version_number)).first()

    # ------------------ COVER LETTERS ------------------
    def save_cover_letter(self, letter_data: Dict[str, Any]) -> CoverLetter:
        data = dict(letter_data)
        if "created_at" not in data or not data["created_at"]:
            data["created_at"] = utcnow_str()
        with self.get_session() as session:
            cl = CoverLetter(**{k: v for k, v in data.items() if hasattr(CoverLetter, k)})
            session.add(cl)
            session.commit()
            session.refresh(cl)
            return cl

    def get_cover_letter(self, letter_id: str) -> Optional[CoverLetter]:
        with self.get_session() as session:
            return session.query(CoverLetter).filter(CoverLetter.letter_id == letter_id).first()

    # ------------------ SEARCH RUNS ------------------
    def create_search_run(self, run_data: Dict[str, Any]) -> SearchRun:
        data = dict(run_data)
        if "started_at" not in data or not data["started_at"]:
            data["started_at"] = utcnow_str()
        if "config_snapshot" in data and isinstance(data["config_snapshot"], (dict, list)):
            data["config_snapshot"] = json.dumps(data["config_snapshot"])
        with self.get_session() as session:
            sr = SearchRun(**{k: v for k, v in data.items() if hasattr(SearchRun, k)})
            session.add(sr)
            session.commit()
            session.refresh(sr)
            return sr

    def finish_search_run(self, run_id: str, stats: Dict[str, Any]) -> Optional[SearchRun]:
        now = utcnow_str()
        with self.get_session() as session:
            sr = session.query(SearchRun).filter(SearchRun.run_id == run_id).first()
            if not sr:
                return None
            sr.completed_at = now
            sr.status = stats.get("status", "COMPLETED")
            for k in ["query_count", "jobs_found", "jobs_new", "jobs_duplicate", "error_message"]:
                if k in stats:
                    setattr(sr, k, stats[k])
            session.commit()
            session.refresh(sr)
            return sr

    # ------------------ APPLICATION EVENTS ------------------
    def record_event(self, application_id: str, event_type: str, event_data: Optional[Dict[str, Any]] = None) -> ApplicationEvent:
        now = utcnow_str()
        data_json = json.dumps(event_data) if event_data else None
        event_id = f"evt_{application_id}_{now}"
        with self.get_session() as session:
            evt = ApplicationEvent(
                event_id=event_id,
                application_id=application_id,
                event_type=event_type,
                event_data=data_json,
                created_at=now,
            )
            session.add(evt)
            session.commit()
            session.refresh(evt)
            return evt

    # ------------------ MATCH FEEDBACK ------------------
    def save_feedback(self, job_id: str, feedback: str, weight_delta: Optional[Dict[str, Any]] = None) -> MatchFeedback:
        now = utcnow_str()
        feedback_id = f"fb_{job_id}_{now}"
        weight_str = json.dumps(weight_delta) if weight_delta else None
        with self.get_session() as session:
            fb = MatchFeedback(
                feedback_id=feedback_id,
                job_id=job_id,
                feedback=feedback,
                weight_delta=weight_str,
                created_at=now,
            )
            session.add(fb)
            session.commit()
            session.refresh(fb)
            return fb
