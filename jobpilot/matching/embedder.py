"""
Semantic Embedding Engine for Bulk Job Pre-Ranking.
Uses nomic-embed-text via Ollama to compute semantic vector similarity
between candidate profile summaries and job postings.
Handles 200+ jobs efficiently in seconds.
"""

import math
from typing import Dict, List, Optional, Tuple
from jobpilot.core.schemas import JobRecord
from jobpilot.llm.factory import get_embedding_provider
from jobpilot.llm.base import EmbeddingProvider


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return round(max(0.0, min(1.0, dot / (norm1 * norm2))), 6)


def fallback_text_similarity(t1: str, t2: str) -> float:
    """Deterministic token overlap similarity fallback if embedding provider is offline."""
    words1 = set(t1.lower().split())
    words2 = set(t2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)


class JobEmbedder:
    """Manages profile and job embedding generation and ranking."""

    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider = provider

    def _ensure_provider(self):
        if self.provider is None:
            self.provider = get_embedding_provider()

    def build_profile_text(self, profile: Dict) -> str:
        """Create a dense summary of candidate skills, degrees, and target roles."""
        skills = []
        for cat in profile.get("skills", {}).values():
            if isinstance(cat, list):
                skills.extend(cat)

        education = profile.get("education", [{}])[0]
        deg = education.get("degree", "")
        field = education.get("field", "")
        exp_years = profile.get("experience", {}).get("total_years_professional", 1)

        summary = (
            f"Candidate: {profile.get('personal', {}).get('full_name', 'Candidate')}. "
            f"Degree: {deg} in {field}. "
            f"Professional Experience: ~{exp_years} year. "
            f"Core Technical Skills: {', '.join(skills)}. "
            f"Target Roles: AI Engineer, AI Automation, LLMs, RAG, Generative AI, Solutions Engineer."
        )
        return summary

    def build_job_text(self, job: JobRecord) -> str:
        """Create dense representation of job title, skills, and summary."""
        desc_snippet = (job.description or "")[:400]
        skills_str = ", ".join(job.skills) if job.skills else ""
        return f"Job Title: {job.title}. Company: {job.company}. Skills: {skills_str}. Details: {desc_snippet}"

    async def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute similarity between two text strings."""
        self._ensure_provider()
        try:
            vecs = await self.provider.embed([text_a, text_b])
            if len(vecs) == 2 and vecs[0] and vecs[1]:
                return cosine_similarity(vecs[0], vecs[1])
        except Exception:
            pass
        return fallback_text_similarity(text_a, text_b)

    async def rank_jobs(
        self,
        profile_text: str,
        jobs: List[JobRecord],
        top_n: int = 30,
    ) -> List[Tuple[JobRecord, float]]:
        """
        Rank a large batch of jobs against the profile text.
        Returns top_n ranked tuples of (JobRecord, embedding_similarity_score).
        """
        if not jobs:
            return []

        self._ensure_provider()
        scores: List[Tuple[JobRecord, float]] = []

        try:
            texts = [self.build_job_text(j) for j in jobs]
            all_texts = [profile_text] + texts
            all_vecs = await self.provider.embed(all_texts)
            if len(all_vecs) == len(all_texts):
                p_vec = all_vecs[0]
                for job, j_vec in zip(jobs, all_vecs[1:]):
                    sim = cosine_similarity(p_vec, j_vec)
                    scores.append((job, sim))
                    job.embedding_vector = j_vec
        except Exception:
            # Fallback when Ollama is offline or unavailable
            for job in jobs:
                j_text = self.build_job_text(job)
                sim = fallback_text_similarity(profile_text, j_text)
                scores.append((job, sim))

        # Sort descending by similarity
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]
