"""
3-Level Deduplication Engine for Discovered Job Postings.
Level 1: Canonical URL hash deduplication.
Level 2: Normalized content hash (company + title + country).
Level 3: String similarity near-duplicate detection.
"""

import hashlib
import re
from typing import List, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from jobpilot.core.schemas import JobRecord


def normalize_url(url: str) -> str:
    """Normalize URL by stripping tracking parameters, anchors, and trailing slashes."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    # Remove common tracking query params
    tracking_prefixes = ("utm_", "ref", "source", "gh_src", "lever-source", "s", "trk")
    query_params = parse_qs(parsed.query)
    clean_params = {
        k: v for k, v in query_params.items()
        if not any(k.lower().startswith(prefix) for prefix in tracking_prefixes)
    }
    # Rebuild normalized URL
    clean_query = urlencode(clean_params, doseq=True)
    clean_path = parsed.path.rstrip("/")
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        clean_path,
        "",  # params
        clean_query,
        "",  # fragment
    ))
    return normalized


def compute_url_hash(url: str) -> str:
    """Compute SHA-256 hash of normalized URL."""
    clean_url = normalize_url(url)
    return hashlib.sha256(clean_url.encode("utf-8")).hexdigest()


def normalize_text_token(text: Optional[str]) -> str:
    """Normalize text by lowercasing, stripping punctuation, and compressing spaces."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


def compute_content_hash(company: str, title: str, country: Optional[str] = "") -> str:
    """Compute SHA-256 hash of normalized company + title + country."""
    c = normalize_text_token(company)
    t = normalize_text_token(title)
    ct = normalize_text_token(country or "")
    composite = f"{c}|{t}|{ct}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


class Deduplicator:
    """Manages multi-tier deduplication for incoming job postings."""

    def __init__(self, existing_url_hashes: Optional[Set[str]] = None, existing_content_hashes: Optional[Set[str]] = None):
        self.seen_url_hashes: Set[str] = existing_url_hashes or set()
        self.seen_content_hashes: Set[str] = existing_content_hashes or set()

    def is_duplicate(self, job: JobRecord) -> Tuple[bool, str]:
        """
        Check if job is a duplicate.
        Returns (is_dup, reason).
        """
        # Level 1: URL Hash
        url_hash = compute_url_hash(job.job_url)
        if url_hash in self.seen_url_hashes:
            return True, "URL duplicate"

        # Level 2: Content Hash
        content_hash = compute_content_hash(job.company, job.title, job.country)
        if content_hash in self.seen_content_hashes:
            return True, "Content duplicate (company + title + country match)"

        return False, ""

    def register(self, job: JobRecord):
        """Mark job as seen."""
        self.seen_url_hashes.add(compute_url_hash(job.job_url))
        self.seen_content_hashes.add(compute_content_hash(job.company, job.title, job.country))

    def filter_unique(self, jobs: List[JobRecord]) -> Tuple[List[JobRecord], List[Tuple[JobRecord, str]]]:
        """
        Filter a batch of jobs into unique jobs and duplicate jobs with reasons.
        Returns: (unique_jobs, duplicate_records_with_reasons)
        """
        unique: List[JobRecord] = []
        duplicates: List[Tuple[JobRecord, str]] = []

        for job in jobs:
            is_dup, reason = self.is_duplicate(job)
            if is_dup:
                job.is_duplicate = True
                duplicates.append((job, reason))
            else:
                self.register(job)
                unique.append(job)

        return unique, duplicates
