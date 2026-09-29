"""
Submission Safety Gate for JobPilot AI.
CRITICAL SAFETY INVARIANT: The system NEVER automatically clicks 'Submit' or finalizes
any job application without the user explicitly typing 'SUBMIT' or confirming in the UI.
"""

import logging
from typing import Callable, Optional
from jobpilot.browser.review_screen import ReviewScreen
from jobpilot.core.safety import SafetyViolation, assert_user_approved
from jobpilot.core.schemas import ApplicationPackage
from jobpilot.database.repository import Repository

logger = logging.getLogger(__name__)


class SubmissionGate:
    """Enforces the explicit user approval gate prior to final application submission."""

    def __init__(self, repo: Optional[Repository] = None):
        self.repo = repo

    def prompt_for_approval(
        self,
        package: ApplicationPackage,
        input_func: Optional[Callable[[str], str]] = None,
    ) -> bool:
        """
        Presents pre-submission review and requires explicit typing of 'SUBMIT'.
        Any other input, whitespace, or cancellation rejects submission.
        """
        # Display review summary
        summary = ReviewScreen.render_cli_summary(package)
        print(summary)

        prompt_func = input_func or input
        try:
            print("\nTo authorize final submission, you must explicitly type 'SUBMIT' below.")
            resp = prompt_func("Confirmation [Type SUBMIT]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[!] Submission cancelled by user.")
            package.user_approved = False
            return False

        if resp == "SUBMIT":
            package.user_approved = True
            logger.info(f"Application {package.application_id} approved by user.")
            print("\n[OK] Application approved for submission.\n")
            return True
        else:
            package.user_approved = False
            logger.warning(f"Application {package.application_id} approval rejected (input: '{resp}').")
            print(f"\n[!] Input was not 'SUBMIT'. Submission blocked for safety.\n")
            return False

    def verify_approved(self, package: ApplicationPackage) -> None:
        """
        Verifies that approval has been granted.
        Raises SafetyViolation if user has not explicitly approved.
        """
        if not package.user_approved:
            raise SafetyViolation(
                f"Application {package.application_id} has not been approved by candidate. "
                f"Automated submission is strictly forbidden."
            )
        if not package.qa_passed:
            raise SafetyViolation(
                f"Application {package.application_id} failed truthfulness QA checks. "
                f"Cannot proceed with submission."
            )
