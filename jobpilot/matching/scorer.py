"""
Multi-Dimensional Scoring Functions for Job Matching.
Calculates granular dimension scores and computes composite weighted fit.
"""

from typing import Any, Dict, List, Optional, Tuple
from jobpilot.core.schemas import JobRecord, MatchStatus, RemotePolicy, VisaStatus
from jobpilot.matching.filters import calculate_experience_penalty


DEFAULT_WEIGHTS = {
    "role_relevance": 0.25,
    "technical_skill": 0.25,
    "experience": 0.20,
    "location_remote": 0.10,
    "immigration": 0.10,
    "seniority": 0.05,
    "education": 0.05,
}


class DimensionScorer:
    """Scores a job posting across all 7 dimensions against candidate profile."""

    def __init__(self, weights: Optional[Dict[str, float]] = None, experience_gap_penalty: float = 0.15):
        self.weights = weights or DEFAULT_WEIGHTS
        self.exp_gap_penalty = experience_gap_penalty

    def score_job(self, job: JobRecord, profile: Dict[str, Any]) -> Tuple[float, MatchStatus, Dict[str, float], List[str], List[str], List[str]]:
        """
        Evaluate job against candidate profile.
        Returns: (composite_score, match_status, dimension_scores, pros, cons, concerns)
        """
        pros: List[str] = []
        cons: List[str] = []
        concerns: List[str] = []
        dim_scores: Dict[str, float] = {}

        # 1. Role Relevance (0.25)
        role_score, r_pro, r_con = self._score_role_relevance(job, profile)
        dim_scores["role_relevance"] = role_score
        if r_pro: pros.append(r_pro)
        if r_con: cons.append(r_con)

        # 2. Technical Skill Match (0.25)
        skill_score, s_pro, s_con = self._score_technical_skills(job, profile)
        dim_scores["technical_skill"] = skill_score
        if s_pro: pros.append(s_pro)
        if s_con: cons.append(s_con)

        # 3. Experience Match (0.20) with soft penalty
        exp_score, e_pro, e_concern = self._score_experience(job, profile)
        dim_scores["experience"] = exp_score
        if e_pro: pros.append(e_pro)
        if e_concern: concerns.append(e_concern)

        # 4. Location / Remote Compatibility (0.10)
        loc_score, l_pro, l_con = self._score_location(job, profile)
        dim_scores["location_remote"] = loc_score
        if l_pro: pros.append(l_pro)
        if l_con: cons.append(l_con)

        # 5. Immigration Feasibility (0.10)
        imm_score, i_pro, i_con = self._score_immigration(job, profile)
        dim_scores["immigration"] = imm_score
        if i_pro: pros.append(i_pro)
        if i_con: cons.append(i_con)

        # 6. Seniority Fit (0.05)
        sen_score = self._score_seniority(job)
        dim_scores["seniority"] = sen_score

        # 7. Education Match (0.05)
        edu_score = self._score_education(job, profile)
        dim_scores["education"] = edu_score

        # Compute weighted sum
        total_weight = sum(self.weights.values())
        raw_composite = sum(dim_scores.get(dim, 0.0) * self.weights.get(dim, 0.0) for dim in self.weights)
        composite = round(raw_composite / total_weight, 2) if total_weight > 0 else 0.0
        composite = max(0.0, min(1.0, composite))

        # Assign MatchStatus
        if composite >= 0.80:
            status = MatchStatus.STRONG_MATCH
        elif composite >= 0.65:
            status = MatchStatus.GOOD_MATCH
        elif composite >= 0.50:
            status = MatchStatus.STRETCH_MATCH
        elif composite >= 0.35:
            status = MatchStatus.POOR_MATCH
        else:
            status = MatchStatus.NO_MATCH

        return composite, status, dim_scores, pros, cons, concerns

    def _score_role_relevance(self, job: JobRecord, profile: Dict) -> Tuple[float, Optional[str], Optional[str]]:
        title = job.title.lower()
        target_families = profile.get("preferences", {}).get("target_role_families", [])

        # Direct exact keywords
        if any(kw in title for kw in ["ai engineer", "generative ai", "llm", "rag", "artificial intelligence"]):
            return 1.0, "High title alignment with AI Engineering target focus", None
        if any(kw in title for kw in ["automation", "make.com", "power automate", "integration"]):
            return 0.90, "Strong alignment with AI Automation focus", None
        if any(kw in title for kw in ["solutions engineer", "applied ai", "data analyst", "product systems"]):
            return 0.80, "Good fit with adjacent solutions & analytics roles", None
        if any(kw in title for kw in ["software engineer", "developer", "machine learning"]):
            return 0.70, "Relevant software/ML role", None

        return 0.40, None, "Title is somewhat peripheral to primary role families"

    def _score_technical_skills(self, job: JobRecord, profile: Dict) -> Tuple[float, Optional[str], Optional[str]]:
        candidate_skills = set()
        for cat in profile.get("skills", {}).values():
            if isinstance(cat, list):
                candidate_skills.update([s.lower() for s in cat])

        if not job.skills:
            # If job didn't parse specific skills, check description
            desc = (job.description or "").lower()
            matched = [s for s in candidate_skills if s in desc]
            if len(matched) >= 3:
                return 0.85, f"Description matches core skills ({', '.join(matched[:3])})", None
            return 0.60, None, None

        job_skills = set([s.lower() for s in job.skills])
        matched = job_skills.intersection(candidate_skills)
        if not matched:
            return 0.30, None, "Few overlapping core skills detected in posting"

        ratio = len(matched) / len(job_skills)
        score = min(1.0, 0.4 + (ratio * 0.6))
        matched_display = [s.title() for s in list(matched)[:4]]
        return round(score, 2), f"Direct skill match on: {', '.join(matched_display)}", None

    def _score_experience(self, job: JobRecord, profile: Dict) -> Tuple[float, Optional[str], Optional[str]]:
        candidate_years = profile.get("experience", {}).get("total_years_professional", 1)
        req_min = job.experience_min

        if req_min is None or req_min <= candidate_years:
            return 1.0, "Experience requirement is directly aligned (~1 year)", None

        penalty, concern = calculate_experience_penalty(req_min, candidate_years, self.exp_gap_penalty)
        score = max(0.20, 1.0 - penalty)
        return round(score, 2), None, concern

    def _score_location(self, job: JobRecord, profile: Dict) -> Tuple[float, Optional[str], Optional[str]]:
        country = (job.country or "").lower()
        remote = job.remote_policy

        if remote == RemotePolicy.REMOTE:
            return 1.0, "Fully remote opportunity matches global preference", None
        if country == "india" or "mumbai" in (job.location or "").lower():
            return 1.0, "Located in domestic market (India)", None
        target_countries = [c.lower() for c in profile.get("preferences", {}).get("target_countries", [])]
        if country in target_countries:
            return 0.85, f"Located in target international country ({job.country})", None

        return 0.50, None, "Non-remote position outside target primary locations"

    def _score_immigration(self, job: JobRecord, profile: Dict) -> Tuple[float, Optional[str], Optional[str]]:
        if (job.country or "").lower() == "india":
            return 1.0, "Domestic authorization — no visa sponsorship required", None

        visa = job.visa_status
        if visa == VisaStatus.SPONSORSHIP_LIKELY or job.sponsor_verified or job.relocation_support:
            return 1.0, "Known sponsor or verified relocation assistance available", None
        if visa == VisaStatus.SPONSORSHIP_POSSIBLE:
            return 0.75, "Eligible international route with potential sponsorship", None
        if visa == VisaStatus.UNCLEAR or visa is None:
            return 0.55, None, "Sponsorship status unclear; requires verification"
        if visa == VisaStatus.SPONSORSHIP_UNLIKELY:
            return 0.30, None, "Low probability of international sponsorship"
        if visa == VisaStatus.NOT_SUITABLE:
            return 0.0, None, "Posting explicitly states foreign applicants not accepted"

        return 0.50, None, None

    def _score_seniority(self, job: JobRecord) -> float:
        title = job.title.lower()
        if any(s in title for s in ["junior", "entry", "associate", "intern", "graduate"]):
            return 1.0
        if any(s in title for s in ["lead", "principal", "staff", "architect", "director", "head of"]):
            return 0.55
        if "senior" in title or "sr" in title:
            return 0.65
        return 0.90  # Mid / un-prefixed standard title

    def _score_education(self, job: JobRecord, profile: Dict) -> float:
        # Candidate holds B.Tech in AI & Data Science
        desc = (job.description or "").lower()
        if any(e in desc for e in ["phd", "ph.d", "doctorate"]):
            return 0.50
        if any(e in desc for e in ["master", "m.tech", "ms in"]):
            return 0.75
        # Bachelor's / Computer Science / AI
        return 1.0
