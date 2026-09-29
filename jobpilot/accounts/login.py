"""
Login and Credential Retrieval Handler for JobPilot AI.
Safely retrieves authentication credentials from Vault and manages account login activity.
"""

from typing import Any, Dict, Optional
from jobpilot.accounts.vault import Vault
from jobpilot.database.models import SiteAccount, utcnow_str
from jobpilot.database.repository import Repository


class LoginManager:
    """Handles credential retrieval and login tracking for automated portal access."""

    def __init__(self, repo: Repository, vault: Optional[Vault] = None):
        self.repo = repo
        self.vault = vault or Vault()

    def get_credentials(self, site_url: str, username: str) -> Optional[Dict[str, str]]:
        """
        Retrieves credentials from Vault for an account.
        Returns dict {"username": username, "password": password, "site_url": site_url} or None.
        """
        clean_url = site_url.strip().lower().rstrip("/")
        password = self.vault.get_password(clean_url, username)
        if not password:
            return None

        return {
            "username": username,
            "password": password,
            "site_url": clean_url,
        }

    def get_account_for_site(self, site_url: str) -> Optional[SiteAccount]:
        """Finds any registered account matching the given site URL/domain."""
        clean_url = site_url.strip().lower().rstrip("/")
        with self.repo.session_scope() as session:
            # First try exact match
            acc = session.query(SiteAccount).filter(SiteAccount.site_url == clean_url).first()
            if acc:
                return acc

            # Try partial domain match
            all_accounts = session.query(SiteAccount).all()
            for a in all_accounts:
                if a.site_url in clean_url or clean_url in a.site_url:
                    return a
            return None

    def record_login(self, account_id: str) -> bool:
        """Updates last_used_at timestamp on the account."""
        with self.repo.session_scope() as session:
            acc = session.query(SiteAccount).filter(SiteAccount.account_id == account_id).first()
            if acc:
                acc.last_used_at = utcnow_str()
                return True
        return False
