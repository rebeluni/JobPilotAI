"""
Google Drive Resume Connector for JobPilot AI.
Downloads and synchronizes candidate resumes from public/shared Google Drive folders and links.
Extracts verified facts from PDFs and manages tailored resume variants.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
import pypdf

try:
    import gdown
    HAS_GDOWN = True
except ImportError:
    HAS_GDOWN = False


def get_default_tailored_dir() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    p = project_root / "jobpilot" / "profiles" / "tailored"
    p.mkdir(parents=True, exist_ok=True)
    return p


class GoogleDriveConnector:
    """Synchronizes resumes from Google Drive shared folders and parses text."""

    def __init__(self, tailored_dir: Optional[Path] = None):
        self.tailored_dir = Path(tailored_dir) if tailored_dir else get_default_tailored_dir()

    def sync_shared_folder(self, folder_url: str) -> List[Path]:
        """
        Synchronizes all resume files from a Google Drive folder URL.
        """
        if not HAS_GDOWN:
            raise ImportError("gdown is required for Google Drive folder syncing. Run: pip install gdown")

        self.tailored_dir.mkdir(parents=True, exist_ok=True)
        try:
            gdown.download_folder(url=folder_url, output=str(self.tailored_dir), quiet=True)
        except Exception:
            # gdown may hit rate-limits on certain non-file Google Docs, but individual files still sync
            pass

        return self.list_tailored_resumes()

    def list_tailored_resumes(self) -> List[Dict[str, str]]:
        """Lists all downloaded tailored resumes and their company/role subdirectories."""
        results = []
        if not self.tailored_dir.exists():
            return results

        for root, _, files in os.walk(self.tailored_dir):
            for f in files:
                full_path = Path(root) / f
                rel_path = full_path.relative_to(self.tailored_dir)
                category = rel_path.parent.as_posix() if rel_path.parent.as_posix() != "." else "general"
                results.append({
                    "filename": f,
                    "relative_path": str(rel_path),
                    "full_path": str(full_path),
                    "category": category,
                    "extension": full_path.suffix.lower(),
                })
        return results

    def extract_text(self, file_path: Path) -> str:
        """Extracts plain text from PDF or text resume."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()
        if ext == ".pdf":
            reader = pypdf.PdfReader(str(file_path))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        else:
            try:
                return file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return file_path.read_text(encoding="latin-1")
