"""
Visa Evidence and Assessment Builder for JobPilot AI.
Extracts immigration-specific signals, generates evidence snippets,
and constructs strictly typed VisaEvidence models with mandatory disclaimers.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from jobpilot.core.schemas import ConfidenceLevel, VisaEvidence, VisaStatus

STANDARD_DISCLAIMER = (
    "This assessment is for informational planning only and does not constitute legal immigration advice."
)

POSITIVE_SPONSOR_PATTERNS = [
    r"\bvisa\s+sponsorship\s+(?:is\s+)?(?:available|provided|offered|possible)\b",
    r"\b(?:we\s+)?sponsor\s+(?:work\s+)?visas?\b",
    r"\bwill\s+sponsor\b",
    r"\brelocation\s+(?:assistance|package|support|allowance|offered|provided)\b",
    r"\bvisa\s+support\b",
    r"\bopen\s+to\s+international\s+(?:applicants|candidates)\b",
    r"\bhelp\s+with\s+(?:relocation|visa)\b",
    r"\bco-sponsor\b",
    r"\btransfer\s+(?:h1b|visa)\b",
]

NEGATIVE_SPONSOR_PATTERNS = [
    r"\bno\s+(?:visa\s+)?sponsorship\b",
    r"\b(?:cannot|can\s+not|unable\s+to|do\s+not|will\s+not|not\s+able\s+to)\s+sponsor\b",
    r"\bnot\s+offering\s+sponsorship\b",
    r"\bsponsorship\s+(?:is\s+)?not\s+available\b",
    r"\bmust\s+have\s+(?:the\s+)?(?:existing\s+|current\s+|valid\s+)?(?:legal\s+)?right\s+to\s+work\b",
    r"\bmust\s+already\s+have\s+work\s+authorization\b",
    r"\bwithout\s+(?:the\s+need\s+for\s+)?(?:future\s+)?sponsorship\b",
    r"\bonly\s+(?:citizens|permanent\s+residents)\b",
    r"\bno\s+relocation\s+(?:assistance|support)\b",
    r"\bsecurity\s+clearance\s+required\b",
    r"\bmust\s+be\s+a\s+(?:us|uk|eu|canadian|australian)\s+citizen\b",
]

KEYWORD_CONTEXT_PATTERNS = [
    r"sponsorship",
    r"visa",
    r"relocation",
    r"work\s+authorization",
    r"work\s+permit",
    r"right\s+to\s+work",
    r"citizenship",
    r"clearance",
]


def extract_evidence_snippets(text: Optional[str]) -> List[str]:
    """
    Extracts sentences from job description or text that contain immigration/visa relevant keywords.
    """
    if not text:
        return []

    snippets = []
    # Split text into rough sentences
    sentences = re.split(r"(?<=[.!?\n])\s+", text)
    compiled_keywords = [re.compile(p, re.IGNORECASE) for p in KEYWORD_CONTEXT_PATTERNS]

    for sentence in sentences:
        clean_sentence = sentence.strip()
        if not clean_sentence or len(clean_sentence) < 10:
            continue
        for kw in compiled_keywords:
            if kw.search(clean_sentence):
                # Trim snippet if overly verbose
                trimmed = clean_sentence[:250].strip()
                if trimmed not in snippets:
                    snippets.append(trimmed)
                break
        if len(snippets) >= 5:  # Cap at 5 key snippets for clarity
            break

    return snippets


def scan_sponsor_signals(text: Optional[str]) -> Tuple[List[str], List[str]]:
    """
    Scans text for positive and negative sponsorship indicator patterns.
    Returns (positive_matches, negative_matches).
    Filters out any positive match that is preceded by negation or overlaps with negative matches.
    """
    if not text:
        return [], []

    neg_matches = []
    for pat in NEGATIVE_SPONSOR_PATTERNS:
        for match in re.finditer(pat, text, re.IGNORECASE):
            neg_matches.append(match.group(0))

    pos_matches = []
    # Negation prefix check: e.g. "no ", "not ", "without ", "unable to "
    negation_prefix = re.compile(r"\b(?:no|not|without|cannot|unable\s+to|never)\s+(?:\w+\s+){0,3}$", re.IGNORECASE)

    for pat in POSITIVE_SPONSOR_PATTERNS:
        for match in re.finditer(pat, text, re.IGNORECASE):
            start = match.start()
            # Inspect preceding context (up to 30 characters)
            preceding = text[max(0, start - 30):start]
            if not negation_prefix.search(preceding):
                # Verify it does not overlap with any negative match
                matched_str = match.group(0)
                if not any(matched_str.lower() in neg.lower() for neg in neg_matches):
                    pos_matches.append(matched_str)

    return pos_matches, neg_matches


def build_visa_evidence(
    country: str,
    visa_status: VisaStatus,
    route: Optional[str] = None,
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN,
    threshold_met: Optional[bool] = None,
    threshold_details: Optional[Dict[str, Any]] = None,
    sponsor_status: Optional[str] = None,
    evidence_snippets: Optional[List[str]] = None,
    verified_rule: bool = False,
) -> VisaEvidence:
    """
    Builds a strictly validated VisaEvidence object.
    Enforces that unverified country rules have confidence capped at LOW (except domestic India).
    Always includes the mandatory legal disclaimer.
    """
    # Enforce confidence capping rule for unverified country immigration thresholds
    final_confidence = confidence
    if country.strip().lower() != "india" and not verified_rule:
        if final_confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
            final_confidence = ConfidenceLevel.LOW

    return VisaEvidence(
        country=country,
        visa_status=visa_status,
        route=route,
        confidence=final_confidence,
        threshold_met=threshold_met,
        threshold_details=threshold_details or {},
        sponsor_status=sponsor_status,
        disclaimer=STANDARD_DISCLAIMER,
        evidence_snippets=evidence_snippets or [],
        verified_rule=verified_rule,
    )
