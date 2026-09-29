"""
Profile Loader for JobPilot AI.
Loads the user's verified facts from the YAML path specified in settings.yaml.
Detects and tracks NEEDS_USER_INPUT unresolved placeholders.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
from jobpilot.core.feature_flags import get_settings


def resolve_profile_path(custom_path: Optional[str] = None) -> Path:
    """Resolve profile path from argument, settings.yaml, or fallback."""
    project_root = Path(__file__).resolve().parent.parent.parent

    if custom_path:
        p = Path(custom_path)
        return p if p.is_absolute() else project_root / p

    settings = get_settings()
    configured_path = settings.get("user", {}).get("profile_path")
    if configured_path:
        p = Path(configured_path)
        return p if p.is_absolute() else project_root / p

    # Fallback default
    return project_root / "jobpilot" / "profiles" / "ankita_profile.yaml"


def count_facts_and_unresolved(data: Any) -> Tuple[int, int, List[str]]:
    """
    Recursively traverse dictionary/list structure and count:
    - verified facts (non-empty, non-NEEDS_USER_INPUT)
    - unresolved items (containing NEEDS_USER_INPUT)
    Returns: (verified_count, needs_input_count, list_of_unresolved_keys)
    """
    verified = 0
    needs_input = 0
    unresolved_keys = []

    def _traverse(node: Any, prefix: str):
        nonlocal verified, needs_input
        if isinstance(node, dict):
            for k, v in node.items():
                new_prefix = f"{prefix}.{k}" if prefix else k
                _traverse(v, new_prefix)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _traverse(item, f"{prefix}[{i}]")
        else:
            val_str = str(node).strip()
            if "NEEDS_USER_INPUT" in val_str or "NEEDS_CONFIG" in val_str:
                needs_input += 1
                unresolved_keys.append(prefix)
            elif val_str != "" and node is not None:
                verified += 1

    _traverse(data, "")
    return verified, needs_input, unresolved_keys


class ProfileLoader:
    """Loads and inspects candidate profiles."""

    def __init__(self, profile_path: Optional[str] = None):
        self.profile_path = resolve_profile_path(profile_path)
        self._data: Optional[Dict[str, Any]] = None

    def load(self, reload: bool = False) -> Dict[str, Any]:
        """Load YAML profile content."""
        if self._data is not None and not reload:
            return self._data

        if not self.profile_path.exists():
            raise FileNotFoundError(f"Profile not found at {self.profile_path}")

        with open(self.profile_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

        return self._data

    load_profile = load

    def get_audit_summary(self) -> Dict[str, Any]:
        """Analyze verified vs unresolved elements."""
        data = self.load()
        verified_count, needs_input_count, unresolved_keys = count_facts_and_unresolved(data)
        return {
            "profile_path": str(self.profile_path),
            "verified_facts_count": verified_count,
            "needs_user_input_count": needs_input_count,
            "unresolved_fields": unresolved_keys,
            "is_ready_for_application": needs_input_count == 0,
        }

    def get_personal(self) -> Dict[str, Any]:
        return self.load().get("personal", {})

    def get_skills(self) -> Dict[str, List[str]]:
        return self.load().get("skills", {})

    def get_work_authorization(self) -> Dict[str, Any]:
        return self.load().get("work_authorization", {})

    def get_master_resume(self) -> Dict[str, Any]:
        return self.load().get("master_resume", {})
