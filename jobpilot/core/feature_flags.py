"""
Feature flags management for JobPilot AI.
Safely checks whether modular components are enabled in settings.yaml.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml

_SETTINGS_CACHE: Optional[Dict[str, Any]] = None


def _find_settings_path() -> Path:
    """Find the path to config/settings.yaml relative to project root."""
    # Current file is in jobpilot/core/feature_flags.py
    project_root = Path(__file__).resolve().parent.parent.parent
    settings_file = project_root / "config" / "settings.yaml"
    return settings_file


def get_settings(reload: bool = False) -> Dict[str, Any]:
    """Load settings from config/settings.yaml."""
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is not None and not reload:
        return _SETTINGS_CACHE

    settings_path = _find_settings_path()
    if not settings_path.exists():
        _SETTINGS_CACHE = {}
        return _SETTINGS_CACHE

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            _SETTINGS_CACHE = yaml.safe_load(f) or {}
    except Exception:
        _SETTINGS_CACHE = {}

    return _SETTINGS_CACHE


def is_enabled(module_name: str) -> bool:
    """
    Check if a specific module is enabled.
    Always safe to call; returns False if missing or disabled.
    """
    settings = get_settings()
    modules = settings.get("modules", {})
    val = modules.get(module_name)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("on", "true", "yes", "1", "enabled")
    return False


def get_all_flags() -> Dict[str, bool]:
    """Return all feature flag states."""
    settings = get_settings()
    modules = settings.get("modules", {})
    flags: Dict[str, bool] = {}
    for k, val in modules.items():
        if isinstance(val, bool):
            flags[k] = val
        elif isinstance(val, str):
            flags[k] = val.strip().lower() in ("on", "true", "yes", "1", "enabled")
        else:
            flags[k] = False
    return flags
