"""
RoleExpander Pipeline Stage for JobPilot AI.
Uses LLM to intelligently expand high-level target role families into specific,
searchable job titles categorized into EXACT, ADJACENT, and STRETCH tiers.
Caches approved expansions in config/role_expansions_cache.yaml with approval workflow.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from jobpilot.core.pipeline import PipelineStage
from jobpilot.core.schemas import RoleExpansion
from jobpilot.llm.base import LLMProvider
from jobpilot.llm.factory import get_llm_provider


def get_default_cache_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "config" / "role_expansions_cache.yaml"


EXPANSION_SCHEMA = {
    "type": "object",
    "properties": {
        "exact_titles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Direct synonyms and exact titles matching the role families",
        },
        "adjacent_titles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Closely related titles with high skill and responsibility overlap",
        },
        "stretch_titles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Aspirational or broader titles that could be suitable stretch opportunities",
        },
    },
    "required": ["exact_titles", "adjacent_titles", "stretch_titles"],
}


class RoleExpander(PipelineStage):
    """Expands role families into comprehensive search keywords across 3 tiers."""

    stage_name: str = "role_expander"

    def __init__(self, llm_provider: Optional[LLMProvider] = None, cache_path: Optional[str] = None):
        self.llm = llm_provider
        self.cache_path = Path(cache_path) if cache_path else get_default_cache_path()

    def _ensure_llm(self):
        if self.llm is None:
            self.llm = get_llm_provider(task="role_expansion")

    def load_cache(self) -> Optional[RoleExpansion]:
        if not self.cache_path.exists():
            return None
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if "role_families" in data:
                return RoleExpansion(**data)
        except Exception:
            return None
        return None

    def save_cache(self, expansion: RoleExpansion) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(expansion.model_dump(), f, sort_keys=False)

    async def expand(self, role_families: List[str], force_refresh: bool = False) -> RoleExpansion:
        """
        Produce role expansion. Returns cached approved version if matching,
        or calls LLM to generate fresh titles for user review.
        """
        cached = self.load_cache()
        if cached and not force_refresh and set(cached.role_families) == set(role_families):
            return cached

        self._ensure_llm()
        prompt = (
            f"You are an expert AI technical recruiter. Given these target career role families: {', '.join(role_families)}.\n"
            f"Generate realistic industry job titles across three tiers:\n"
            f"1. EXACT: Direct, standard title matches (e.g. AI Engineer, LLM Engineer).\n"
            f"2. ADJACENT: Close titles with high skill overlap for early career / AI automation (e.g. Automation Developer, AI Integration Specialist).\n"
            f"3. STRETCH: Slightly broader or higher scope titles suitable as stretch goals (e.g. Solutions Architect).\n"
            f"Avoid pure DevOps, Linux SysAdmin, and Java/Spring roles."
        )

        try:
            data = await self.llm.structured_output(prompt, EXPANSION_SCHEMA)
            expansion = RoleExpansion(
                role_families=role_families,
                exact_titles=data.get("exact_titles", []),
                adjacent_titles=data.get("adjacent_titles", []),
                stretch_titles=data.get("stretch_titles", []),
                approved=False,
                pending_review=True,
            )
        except Exception:
            # Safe heuristic fallback if LLM is unavailable
            expansion = self._fallback_expansion(role_families)

        self.save_cache(expansion)
        return expansion

    def approve_expansion(self) -> Optional[RoleExpansion]:
        """Mark currently cached expansion as user-approved."""
        cached = self.load_cache()
        if cached:
            cached.approved = True
            cached.pending_review = False
            self.save_cache(cached)
            return cached
        return None

    def _fallback_expansion(self, role_families: List[str]) -> RoleExpansion:
        """Deterministic fallback when LLM is offline."""
        exact = []
        adjacent = []
        stretch = []

        for rf in role_families:
            clean = rf.replace("_", " ").title()
            exact.append(clean)
            if "Ai" in clean:
                adjacent.append(f"{clean} Specialist")
                adjacent.append(f"Generative {clean}")
            elif "Automation" in clean:
                adjacent.append("Workflow Automation Developer")
                adjacent.append("Make.com / Integration Specialist")
            stretch.append(f"Senior {clean}")

        return RoleExpansion(
            role_families=role_families,
            exact_titles=list(set(exact)),
            adjacent_titles=list(set(adjacent)),
            stretch_titles=list(set(stretch)),
            approved=False,
            pending_review=True,
        )

    async def run(self, input_data: Any) -> RoleExpansion:
        if isinstance(input_data, list):
            return await self.expand(input_data)
        return self._fallback_expansion(["AI_ENGINEER"])
