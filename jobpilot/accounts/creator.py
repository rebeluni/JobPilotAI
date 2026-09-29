"""
Account Creator and Strong Password Generator for JobPilot AI.
Generates cryptographically secure passwords conforming to enterprise ATS complexity rules.
Securely registers accounts into Vault and local SQLite repository.
"""

import re
import secrets
import string
from typing import List, Optional, Tuple
from jobpilot.accounts.vault import Vault
from jobpilot.database.models import SiteAccount
from jobpilot.database.repository import Repository

SPECIAL_CHARS = "!@#$%^&*()-_=+"


def generate_strong_password(
    length: int = 16,
    require_upper: bool = True,
    require_lower: bool = True,
    require_digits: bool = True,
    require_special: bool = True,
) -> str:
    """
    Generates a cryptographically strong random password satisfying ATS requirements.
    Guarantees at least one character from each required category.
    """
    if length < 12:
        length = 12

    required_chars: List[str] = []
    pool: List[str] = []

    if require_lower:
        required_chars.append(secrets.choice(string.ascii_lowercase))
        pool.extend(string.ascii_lowercase)
    if require_upper:
        required_chars.append(secrets.choice(string.ascii_uppercase))
        pool.extend(string.ascii_uppercase)
    if require_digits:
        required_chars.append(secrets.choice(string.digits))
        pool.extend(string.digits)
    if require_special:
        required_chars.append(secrets.choice(SPECIAL_CHARS))
        pool.extend(SPECIAL_CHARS)

    remaining_length = length - len(required_chars)
    for _ in range(remaining_length):
        required_chars.append(secrets.choice(pool))

    # Cryptographically secure shuffle using SystemRandom
    rng = secrets.SystemRandom()
    rng.shuffle(required_chars)
    return "".join(required_chars)


def validate_password_complexity(password: str) -> Tuple[bool, List[str]]:
    """
    Validates password strength against standard enterprise complexity rules.
    Returns (is_valid, list_of_deficiencies).
    """
    errors: List[str] = []
    if len(password) < 10:
        errors.append("Password must be at least 10 characters long")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_\-+=\[\]{}|;:,.<>?]", password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


def create_site_account(
    repo: Repository,
    site_url: str,
    username: str,
    site_name: Optional[str] = None,
    password: Optional[str] = None,
    vault: Optional[Vault] = None,
    notes: Optional[str] = None,
) -> SiteAccount:
    """
    Creates or registers an account for an ATS or job portal.
    Password is saved ONLY into OS Keyring / Vault, NEVER into SQLite database.
    """
    vault = vault or Vault()

    if not password:
        password = generate_strong_password()

    is_valid, errors = validate_password_complexity(password)
    if not is_valid:
        raise ValueError(f"Password fails complexity validation: {', '.join(errors)}")

    # Clean site URL for consistent identification
    clean_url = site_url.strip().lower().rstrip("/")
    if not site_name:
        # Extract domain name as default site name
        domain_match = re.search(r"(?:https?://)?(?:www\.)?([^/]+)", clean_url)
        site_name = domain_match.group(1) if domain_match else "JobPortal"

    # Save to secure vault
    stored = vault.store_password(clean_url, username, password)
    if not stored:
        raise RuntimeError(f"Failed to store password in vault for {clean_url}")

    # Generate account_id
    account_id = f"acc_{site_name.lower().replace('.', '_')}_{username.split('@')[0]}"

    account_data = {
        "account_id": account_id,
        "site_url": clean_url,
        "site_name": site_name,
        "username": username,
        "notes": notes or f"Registered via JobPilot AI on {clean_url}",
    }

    return repo.upsert_site_account(account_data)
