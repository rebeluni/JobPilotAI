"""
Human-in-the-Loop Handoff Manager for JobPilot AI.
Detects Bot Challenges (Cloudflare Turnstile, reCAPTCHA, hCaptcha), 2FA/MFA,
and unresolved application questions requiring human input.
Safely halts automated execution and requests candidate action.
"""

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

CAPTCHA_PATTERNS = [
    r"cf-turnstile",
    r"challenges\.cloudflare\.com",
    r"recaptcha",
    r"g-recaptcha",
    r"google\.com/recaptcha",
    r"hcaptcha\.com",
    r"h-captcha",
    r"arkoselabs",
    r"funcaptcha",
    r"geetest",
]

MFA_PATTERNS = [
    r"two-factor\s+authentication",
    r"2-step\s+verification",
    r"enter\s+(?:the\s+)?verification\s+code",
    r"security\s+code\s+sent\s+to",
    r"authenticator\s+app",
]


class HandoffManager:
    """Manages detection of challenges and human handoff coordination."""

    def check_for_challenge(self, html_content: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Scans DOM HTML for bot challenges, captchas, or multi-factor authentication requests.
        Returns (needs_handoff, reason).
        """
        if not html_content:
            return False, None

        html_lower = html_content.lower()

        # Check Captcha patterns
        for pat in CAPTCHA_PATTERNS:
            if re.search(pat, html_lower):
                return True, f"Security challenge detected ({pat}). Human intervention required to solve captcha."

        # Check MFA patterns
        for pat in MFA_PATTERNS:
            if re.search(pat, html_lower):
                return True, "Two-factor authentication (2FA/MFA) prompt detected. Please complete verification."

        return False, None

    def check_unresolved_answers(self, unresolved_fields: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Checks if required application questions are unresolved.
        """
        if unresolved_fields:
            fields_str = ", ".join(unresolved_fields[:5])
            return True, f"Required questions need candidate input: {fields_str}"
        return False, None

    def display_handoff_banner(self, reason: str) -> None:
        """Prints a prominent visual alert in the console for candidate action."""
        border = "=" * 70
        print("\n" + border)
        print(" [!] JOBPILOT AI — CANDIDATE ACTION REQUIRED (HUMAN HANDOFF)")
        print(border)
        print(f" Reason: {reason}")
        print(" Instructions:")
        print("  1. Please interact directly with the opened browser window.")
        print("  2. Complete the required captcha, 2FA, or form fields.")
        print("  3. Do NOT submit the application yet.")
        print(border + "\n")
        logger.warning(f"Human handoff triggered: {reason}")
