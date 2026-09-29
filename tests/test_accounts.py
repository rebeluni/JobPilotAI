"""
Tests for JobPilot AI Account and Session Management.
Verifies password vault storage, password complexity rules, zero plaintext in database,
login handling, OTP and verification link extraction, and browser session persistence.
"""

import json
from pathlib import Path
import pytest
from jobpilot.accounts.creator import (
    create_site_account,
    generate_strong_password,
    validate_password_complexity,
)
from jobpilot.accounts.email_verifier import EmailVerifier, extract_otp, extract_verification_link
from jobpilot.accounts.login import LoginManager
from jobpilot.accounts.session_manager import SessionManager
from jobpilot.accounts.vault import Vault
from jobpilot.database.models import SiteAccount
from jobpilot.database.repository import Repository


@pytest.fixture
def temp_repo(tmp_path):
    db_file = tmp_path / "test_accounts.db"
    db_url = f"sqlite:///{db_file}"
    repo = Repository(db_url=db_url)
    repo.init_db()
    try:
        yield repo
    finally:
        repo.engine.dispose()


@pytest.fixture
def temp_vault(tmp_path):
    return Vault(use_fallback_only=True, fallback_path=tmp_path / "test_vault.enc")


class TestVault:
    def test_store_and_retrieve_password(self, temp_vault):
        site = "https://boards.greenhouse.io/deepmind"
        user = "ankita@example.com"
        pwd = "SecureP@ssw0rd!2026"

        assert temp_vault.store_password(site, user, pwd) is True
        assert temp_vault.has_password(site, user) is True
        retrieved = temp_vault.get_password(site, user)
        assert retrieved == pwd

    def test_delete_password(self, temp_vault):
        site = "lever.co/company"
        user = "test_user"
        temp_vault.store_password(site, user, "Sample!123456")
        assert temp_vault.has_password(site, user) is True
        temp_vault.delete_password(site, user)
        assert temp_vault.has_password(site, user) is False
        assert temp_vault.get_password(site, user) is None

    def test_missing_password_returns_none(self, temp_vault):
        assert temp_vault.get_password("nonexistent.com", "user") is None


class TestPasswordGeneratorAndValidator:
    def test_generate_strong_password(self):
        pwd = generate_strong_password(length=18)
        assert len(pwd) == 18
        is_valid, errors = validate_password_complexity(pwd)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_complexity_failures(self):
        is_valid, errors = validate_password_complexity("short")
        assert is_valid is False
        assert any("at least 10" in e for e in errors)

        is_valid, errors = validate_password_complexity("alllowercase123!")
        assert is_valid is False
        assert any("uppercase" in e for e in errors)

        is_valid, errors = validate_password_complexity("NoDigitsOrSpecialLetters")
        assert is_valid is False
        assert any("digit" in e for e in errors)
        assert any("special" in e for e in errors)


class TestAccountCreationAndLogin:
    def test_create_site_account_zero_plaintext_in_db(self, temp_repo, temp_vault):
        site_url = "https://jobs.lever.co/techcorp"
        username = "ankita.yadav@example.com"

        account = create_site_account(
            repo=temp_repo,
            site_url=site_url,
            username=username,
            vault=temp_vault,
        )

        assert account is not None
        assert account.username == username
        assert "techcorp" in account.site_name.lower() or "lever" in account.site_name.lower()

        # Verify password is in vault
        pwd = temp_vault.get_password(site_url, username)
        assert pwd is not None
        assert len(pwd) >= 12

        # Verify password is NOT stored anywhere in the database model
        with temp_repo.session_scope() as session:
            db_acc = session.query(SiteAccount).filter(SiteAccount.account_id == account.account_id).first()
            assert db_acc is not None
            # Check all attributes of db_acc to confirm raw password is not present
            for col in SiteAccount.__table__.columns:
                val = getattr(db_acc, col.name)
                assert val != pwd

    def test_login_manager(self, temp_repo, temp_vault):
        site_url = "https://boards.greenhouse.io/anthropic"
        username = "applicant@example.com"
        account = create_site_account(
            repo=temp_repo,
            site_url=site_url,
            username=username,
            vault=temp_vault,
        )

        login_mgr = LoginManager(repo=temp_repo, vault=temp_vault)
        creds = login_mgr.get_credentials(site_url, username)
        assert creds is not None
        assert creds["username"] == username
        assert len(creds["password"]) >= 12

        # Record login
        assert login_mgr.record_login(account.account_id) is True
        with temp_repo.session_scope() as session:
            db_acc = session.query(SiteAccount).filter(SiteAccount.account_id == account.account_id).first()
            assert db_acc.last_used_at is not None


class TestEmailVerifier:
    def test_extract_otp(self):
        text1 = "Your verification code is: 489201. Please enter it within 10 minutes."
        assert extract_otp(text1) == "489201"

        text2 = "Security PIN: 9381. Do not share this with anyone."
        assert extract_otp(text2) == "9381"

        text3 = "Thank you for registering. Enter code 729103 to complete sign up."
        assert extract_otp(text3) == "729103"

    def test_extract_verification_link(self):
        email_body = (
            "Welcome to Greenhouse Careers!\n"
            "Please verify your account by clicking the link below:\n"
            "https://boards.greenhouse.io/auth/verify?token=abc123xyz789\n"
            "This link will expire in 24 hours."
        )
        link = extract_verification_link(email_body)
        assert link is not None
        assert "https://boards.greenhouse.io/auth/verify?token=abc123xyz789" in link

    def test_email_verifier_service(self):
        verifier = EmailVerifier()
        assert verifier.extract_otp_code("Your one-time passcode is 628401.") == "628401"
        assert verifier.extract_link("Click here to confirm: https://example.com/activate?id=99") == "https://example.com/activate?id=99"


class TestSessionManager:
    def test_save_and_load_session(self, tmp_path):
        mgr = SessionManager(sessions_dir=tmp_path)
        site = "https://jobs.lever.co/sample"
        state = {
            "cookies": [{"name": "session_id", "value": "xyz123", "domain": ".lever.co"}],
            "origins": [],
        }

        path = mgr.save_session(site, state)
        assert path.exists()

        loaded = mgr.load_session(site)
        assert loaded == state
        assert mgr.has_valid_session(site) is True

        # Delete session
        assert mgr.delete_session(site) is True
        assert mgr.has_valid_session(site) is False
        assert mgr.load_session(site) is None
