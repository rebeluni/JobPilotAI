"""
Immigration Routes and Rules Loader for JobPilot AI.
Loads dynamic thresholds and policy links from config/immigration_rules.yaml.
Never hardcodes thresholds in code; verifies rule verification status.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml


def get_default_rules_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "config" / "immigration_rules.yaml"


class RouteManager:
    """Manages country immigration criteria and official verification states."""

    def __init__(self, rules_path: Optional[str] = None):
        self.rules_path = Path(rules_path) if rules_path else get_default_rules_path()
        self._rules: Optional[Dict[str, Any]] = None

    def load_rules(self, reload: bool = False) -> Dict[str, Any]:
        if self._rules is not None and not reload:
            return self._rules
        if not self.rules_path.exists():
            return {}
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self._rules = data.get("countries", {})
        except Exception:
            self._rules = {}
        return self._rules or {}

    def get_country_rule(self, country: Optional[str]) -> Optional[Dict[str, Any]]:
        if not country:
            return None
        rules = self.load_rules()
        for k, v in rules.items():
            if k.lower() == country.lower():
                return v
        return None

    def is_rule_verified(self, country: Optional[str]) -> bool:
        """Return True only if the user has manually checked and set verified: true."""
        rule = self.get_country_rule(country)
        if not rule:
            return False
        return bool(rule.get("verified", False))

    def get_route_name(self, country: Optional[str]) -> str:
        rule = self.get_country_rule(country)
        if rule:
            return rule.get("route", "General Skilled Worker")
        return "Unknown Route"
