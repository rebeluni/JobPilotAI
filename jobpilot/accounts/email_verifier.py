"""
Email Verification and OTP Code Extractor for JobPilot AI.
Extracts account activation links and multi-digit OTP/verification codes from emails,
with graceful manual input fallback for human-in-the-loop assistance.
"""

import re
from typing import List, Optional

OTP_PATTERNS = [
    r"(?:verification|security|confirmation|login|auth|one-time|otp|pin)\s+(?:code|pin|password|token)?(?:\s+is)?[:\s]+([0-9]{4,8})\b",
    r"\bcode[:\s]+([0-9]{4,8})\b",
    r"\b([0-9]{6})\b",  # Standard 6-digit standalone code
    r"\b([0-9]{4})\b",  # Standard 4-digit code
]

LINK_KEYWORDS = [
    "verify",
    "verification",
    "activate",
    "activation",
    "confirm",
    "confirmation",
    "validate",
    "token",
    "auth",
]


def extract_otp(body: Optional[str]) -> Optional[str]:
    """
    Extracts a numeric verification code / OTP (4-8 digits) from an email body.
    Prioritizes explicit keywords before falling back to standalone digit sequences.
    """
    if not body:
        return None

    # First check context-based patterns
    for pat in OTP_PATTERNS[:2]:
        match = re.search(pat, body, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Second check standalone 6-digit or 4-digit patterns
    for pat in OTP_PATTERNS[2:]:
        for match in re.finditer(pat, body):
            candidate = match.group(1).strip()
            # Avoid matching years like 2024, 2025, 2026 if 4-digit
            if len(candidate) == 4 and candidate.startswith(("19", "20")):
                continue
            return candidate

    return None


def extract_verification_link(body: Optional[str]) -> Optional[str]:
    """
    Extracts an activation/verification URL from email text or HTML content.
    Filters URLs based on common activation query params and path tokens.
    """
    if not body:
        return None

    # Match HTTP/HTTPS URLs
    url_pattern = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
    urls: List[str] = url_pattern.findall(body)

    for url in urls:
        # Clean trailing punctuation
        clean_url = re.sub(r"[.,;:!?)\]]+$", "", url)
        lower_url = clean_url.lower()

        # Check if URL contains activation or confirmation tokens
        if any(kw in lower_url for kw in LINK_KEYWORDS):
            return clean_url

    # Fallback: if single URL present and text mentions confirm/verify
    if len(urls) == 1 and any(kw in body.lower() for kw in LINK_KEYWORDS):
        return re.sub(r"[.,;:!?)\]]+$", "", urls[0])

    return None


class EmailVerifier:
    """Service for extracting and validating verification credentials."""

    def extract_otp_code(self, message_text: str) -> Optional[str]:
        return extract_otp(message_text)

    def extract_link(self, message_text: str) -> Optional[str]:
        return extract_verification_link(message_text)

    def manual_code_prompt(self, site_name: str) -> str:
        """Interactive fallback prompting candidate for OTP code."""
        print(f"\n[JobPilot AI] Verification code required for {site_name}.")
        code = input("Please enter the verification code received by email: ").strip()
        return code
