"""
Dynamic Search Query Builder for Job Discovery.
Generates targeted queries combining role family keywords, target countries,
and major ATS board search operators (Greenhouse, Lever, Ashby, Workable, etc.).
"""

from typing import Any, Dict, List, Optional
from jobpilot.core.feature_flags import get_settings


ATS_OPERATORS = [
    "site:boards.greenhouse.io",
    "site:jobs.lever.co",
    "site:ashbyhq.com",
    "site:jobs.smartrecruiters.com",
    "site:apply.workable.com",
]


class QueryBuilder:
    """Constructs effective search queries for SearXNG and search engines."""

    def __init__(self, role_families_config: Optional[Dict[str, Any]] = None):
        self.role_families = role_families_config or {}

    def build_ats_queries(
        self,
        role_keywords: List[str],
        countries: List[str],
        ats_operators: Optional[List[str]] = None,
        remote: bool = True,
    ) -> List[str]:
        """Generate targeted ATS site search queries."""
        operators = ats_operators or ATS_OPERATORS
        queries: List[str] = []

        # Format role term: ("Keyword 1" OR "Keyword 2")
        role_clause = " OR ".join([f'"{kw}"' for kw in role_keywords[:4]])
        if len(role_keywords) > 1:
            role_clause = f"({role_clause})"

        for country in countries:
            loc_clause = f'("{country}" OR "Remote")' if remote else f'"{country}"'
            for op in operators:
                q = f"{op} {role_clause} {loc_clause}"
                queries.append(q)

        return queries

    def build_immigration_queries(
        self,
        role_keywords: List[str],
        countries: List[str],
    ) -> List[str]:
        """Generate queries targeted at sponsored or relocation-supported roles."""
        queries: List[str] = []
        role_clause = " OR ".join([f'"{kw}"' for kw in role_keywords[:3]])
        if len(role_keywords) > 1:
            role_clause = f"({role_clause})"

        sponsor_terms = '("visa sponsorship" OR "relocation support" OR "sponsorship available" OR "international applicants")'

        for country in countries:
            if country.lower() != "india":
                q = f"{role_clause} {sponsor_terms} \"{country}\""
                queries.append(q)

        return queries

    def build_general_queries(
        self,
        role_keywords: List[str],
        countries: List[str],
        remote_only: bool = False,
    ) -> List[str]:
        """Generate general web discovery queries."""
        queries: List[str] = []
        role_clause = " OR ".join([f'"{kw}"' for kw in role_keywords[:3]])
        if len(role_keywords) > 1:
            role_clause = f"({role_clause})"

        for country in countries:
            loc_term = f'"{country}" Remote' if remote_only else f'"{country}"'
            q = f"{role_clause} careers {loc_term} -intitle:profiles -intitle:resumes"
            queries.append(q)

        return queries
