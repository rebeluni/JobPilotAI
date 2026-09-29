"""
Tests for Google Drive Resume Connector.
Verifies discovery, listing, and text extraction from synced tailored resumes.
"""

from pathlib import Path
import pytest
from jobpilot.profiles.google_drive_connector import GoogleDriveConnector, get_default_tailored_dir


def test_google_drive_connector_discovery():
    """Verify that tailored resumes directory is inspected properly."""
    connector = GoogleDriveConnector()
    resumes = connector.list_tailored_resumes()
    
    # We downloaded files into jobpilot/profiles/tailored/
    assert isinstance(resumes, list)
    if resumes:
        first = resumes[0]
        assert "filename" in first
        assert "category" in first
        assert "full_path" in first
        assert "extension" in first


def test_google_drive_connector_text_extraction(tmp_path):
    """Verify text extraction from sample text/markdown resume file."""
    sample_file = tmp_path / "sample_resume.txt"
    sample_file.write_text("Ankita Yadav - AI Engineer - Python, LLMs, RAG", encoding="utf-8")
    
    connector = GoogleDriveConnector(tailored_dir=tmp_path)
    text = connector.extract_text(sample_file)
    assert "Ankita Yadav" in text
    assert "Python, LLMs, RAG" in text


def test_google_drive_connector_missing_file_raises():
    """Verify error on non-existent file."""
    connector = GoogleDriveConnector()
    with pytest.raises(FileNotFoundError):
        connector.extract_text(Path("non_existent_resume_file.pdf"))
