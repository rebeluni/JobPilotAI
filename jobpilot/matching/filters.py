"""
Hard Filters and Soft Penalty Rules for Job Matching.
Applies domain-specific career constraints without prematurely rejecting stretch opportunities.
"""

from typing import Dict, List, Optional, Tuple
import re

from jobpilot.core.schemas import JobRecord, MatchStatus, VisaStatus


HARD_AVOID_PATTERNS = [
    r"\bdevops engineer\b",
    r"\bsre\b",
    r"\bsite reliability\b",
    r"\blinux (?:system |sys)?admin\b",
    r"\binfrastructure engineer\b",
    r"\bcloud infrastructure\b",
    r"\bjava\b.*\bspring\b",
    r"\bembedded\b",
    r"\bfirmware\b",
]


def check_hard_filters(job: JobRecord) -> Tuple[bool, Optional[str]]:
    """
    Check if a job fails any non-negotiable hard rejection criteria.
    Returns: (is_rejected, rejection_reason)
    """
    title_lower = job.title.lower()
    desc_lower = (job.description or "").lower()
    combined = f"{title_lower} {desc_lower[:500]}"

    # 1. Avoided role domains (Pure DevOps, SysAdmin, Firmware)
    for pattern in HARD_AVOID_PATTERNS:
        if re.search(pattern, title_lower):
            # If the title explicitly says DevOps / SRE / SysAdmin
            return True, f"Hard filter: Title matches avoided career category ({pattern})"

    # 2. Java / Spring primary with zero Python / AI
    if "java" in title_lower or "spring" in title_lower:
        if "python" not in combined and "ai" not in combined and "machine learning" not in combined:
            return True, "Hard filter: Java/Spring primary role without Python or AI focus"

    # 3. Explicitly unsuitable immigration
    if job.visa_status == VisaStatus.NOT_SUITABLE:
        return True, "Hard filter: Posting explicitly excludes foreign / visa applicants"

    return False, None


def calculate_experience_penalty(
    required_years_min: Optional[int],
    candidate_years: int = 1,
    penalty_per_year: float = 0.15,
) -> Tuple[float, Optional[str]]:
    """
    Compute a soft penalty when candidate experience is less than stated requirement.
    Never auto-rejects; returns (penalty_score_deduction, concern_explanation).
    """
    if required_years_min is None or required_years_min <= candidate_years:
        return 0.0, None

    gap = required_years_min - candidate_years
    total_penalty = round(min(0.60, gap * penalty_per_year), 2)
    concern = (
        f"Stated requirement is {required_years_min}+ years (candidate has ~{candidate_years} yr). "
        f"Soft penalty of -{total_penalty:.2f} applied to experience dimension."
    )
    return total_penalty, concern
