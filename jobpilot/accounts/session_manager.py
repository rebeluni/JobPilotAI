"""
Browser Session Manager for JobPilot AI.
Persists and restores Playwright browser session states (cookies, origins, local storage)
in the designated external JobPilotData/sessions/ directory.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def get_default_sessions_dir() -> Path:
    from jobpilot.database.repository import get_data_dir
    data_dir = get_data_dir()
    sessions_dir = data_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def _site_slug(site_url: str) -> str:
    """Creates a filesystem-safe slug from a site URL or domain."""
    clean = site_url.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    slug = re.sub(r"[^\w\-.]", "_", clean)
    return slug[:100]


class SessionManager:
    """Manages serialization and lifespan of browser storage states."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = Path(sessions_dir) if sessions_dir else get_default_sessions_dir()
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def get_session_path(self, site_url: str) -> Path:
        slug = _site_slug(site_url)
        return self.sessions_dir / f"{slug}_session.json"

    def save_session(self, site_url: str, storage_state: Dict[str, Any]) -> Path:
        """
        Saves Playwright storage_state dict (cookies, local storage) to a JSON file.
        Returns the saved file path.
        """
        path = self.get_session_path(site_url)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(storage_state, f, indent=2)
            logger.info(f"Saved browser session for {site_url} to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to save session for {site_url}: {e}")
            raise

    def load_session(self, site_url: str) -> Optional[Dict[str, Any]]:
        """
        Loads the saved storage_state dict for a site.
        Returns None if session file does not exist or cannot be parsed.
        """
        path = self.get_session_path(site_url)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load session from {path}: {e}")
            return None

    def has_valid_session(self, site_url: str, max_age_days: int = 7) -> bool:
        """
        Checks if a valid, unexpired session file exists for the site.
        """
        path = self.get_session_path(site_url)
        if not path.exists():
            return False

        file_age_seconds = time.time() - os.path.getmtime(path)
        max_age_seconds = max_age_days * 86400
        return file_age_seconds <= max_age_seconds

    def delete_session(self, site_url: str) -> bool:
        """Removes the session state file for a site."""
        path = self.get_session_path(site_url)
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as e:
                logger.error(f"Failed to delete session file {path}: {e}")
                return False
        return False
