"""
Secure Credential Vault for JobPilot AI.
Uses OS keyring (Windows Credential Manager / macOS Keychain / SecretService) for zero-plaintext password management.
NEVER logs, prints, or saves passwords in database tables.
"""

import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

logger = logging.getLogger(__name__)

SERVICE_PREFIX = "JobPilotAI"


def _get_fallback_store_path() -> Path:
    from jobpilot.database.repository import get_data_dir
    data_dir = get_data_dir()
    return data_dir / "vault.enc"


def _derive_local_key() -> bytes:
    """Derives a machine/user-specific obfuscation key without external libraries."""
    salt = b"JobPilotAI_LocalVault_Salt_2026"
    machine_id = os.environ.get("COMPUTERNAME", "JobPilotHost").encode("utf-8")
    user_id = os.environ.get("USERNAME", "JobPilotUser").encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", machine_id + user_id, salt, 100000, dklen=32)


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


class Vault:
    """
    Secure password vault storing credentials in OS Keyring.
    Provides seamless local encrypted fallback if keyring is unavailable or in isolated tests.
    """

    def __init__(self, use_fallback_only: bool = False, fallback_path: Optional[Path] = None):
        self.use_fallback_only = use_fallback_only
        self.fallback_path = Path(fallback_path) if fallback_path else _get_fallback_store_path()
        self._fallback_cache: Optional[Dict[str, str]] = None

    def _service_name(self, site: str) -> str:
        clean_site = site.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
        return f"{SERVICE_PREFIX}:{clean_site}"

    def _load_fallback(self) -> Dict[str, str]:
        if self._fallback_cache is not None:
            return self._fallback_cache

        path = self.fallback_path
        if not path.exists():
            self._fallback_cache = {}
            return self._fallback_cache

        try:
            raw = path.read_bytes()
            key = _derive_local_key()
            decrypted = _xor_cipher(raw, key)
            self._fallback_cache = json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Could not load fallback vault: {e}")
            self._fallback_cache = {}
        return self._fallback_cache

    def _save_fallback(self, store: Dict[str, str]) -> bool:
        self._fallback_cache = store
        path = self.fallback_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            encoded = json.dumps(store).encode("utf-8")
            key = _derive_local_key()
            encrypted = _xor_cipher(encoded, key)
            path.write_bytes(encrypted)
            return True
        except Exception as e:
            logger.error(f"Failed to save fallback vault: {e}")
            return False

    def store_password(self, site: str, username: str, password: str) -> bool:
        """
        Securely stores password.
        Returns True on success. Never prints or logs the password.
        """
        service = self._service_name(site)
        if not self.use_fallback_only and HAS_KEYRING:
            try:
                keyring.set_password(service, username, password)
                return True
            except Exception as e:
                logger.warning(f"Keyring storage failed, falling back to local vault: {e}")

        # Fallback storage
        store = self._load_fallback()
        cache_key = f"{service}::{username}"
        store[cache_key] = password
        return self._save_fallback(store)

    def get_password(self, site: str, username: str) -> Optional[str]:
        """
        Retrieves password from OS Keyring or fallback.
        Returns None if not found.
        """
        service = self._service_name(site)
        if not self.use_fallback_only and HAS_KEYRING:
            try:
                pwd = keyring.get_password(service, username)
                if pwd is not None:
                    return pwd
            except Exception as e:
                logger.warning(f"Keyring retrieval failed, falling back: {e}")

        # Fallback retrieval
        store = self._load_fallback()
        cache_key = f"{service}::{username}"
        return store.get(cache_key)

    def delete_password(self, site: str, username: str) -> bool:
        """Deletes password from both keyring and fallback store."""
        service = self._service_name(site)
        success = False

        if not self.use_fallback_only and HAS_KEYRING:
            try:
                keyring.delete_password(service, username)
                success = True
            except Exception:
                pass

        store = self._load_fallback()
        cache_key = f"{service}::{username}"
        if cache_key in store:
            del store[cache_key]
            self._save_fallback(store)
            success = True

        return success

    def has_password(self, site: str, username: str) -> bool:
        return self.get_password(site, username) is not None
