"""
Hybrid 2-Stage Matching Engine for JobPilot AI.
Stage 1: Fast semantic pre-ranking using nomic-embed-text embeddings.
Stage 2: Multi-dimensional scoring + LLM synthesis producing MatchResult schemas.
"""

from typing import Any, Dict, List, Optional, Tuple
from jobpilot.core.pipeline import PipelineStage
from jobpilot.core.schemas import JobRecord, MatchResult, MatchStatus
from jobpilot.core.feature_flags import get_settings
from jobpilot.matching.embedder import JobEmbedder
from jobpilot.matching.scorer import DimensionScorer
from jobpilot.matching.filters import check_hard_filters
from jobpilot.profiles.loader import ProfileLoader
from jobpilot.llm.base import LLMProvider
from jobpilot.llm.factory import get_llm_provider


class MatchingEngine(PipelineStage):
    """Orchestrates job matching across embedding pre-ranking and dimension scoring."""

    stage_name: str = "matching_engine"

    def __init__(
        self,
        embedder: Optional[JobEmbedder] = None,
        scorer: Optional[DimensionScorer] = None,
        llm: Optional[LLMProvider] = None,
        profile_loader: Optional[ProfileLoader] = None,
    ):
        settings = get_settings().get("matching", {})
        weights = settings.get("weights")
        exp_gap_penalty = settings.get("experience_gap_penalty", 0.15)
        self.top_n = settings.get("embedding_top_n", 30)

        self.embedder = embedder or JobEmbedder()
        self.scorer = scorer or DimensionScorer(weights=weights, experience_gap_penalty=exp_gap_penalty)
        self.llm = llm
        self.profile_loader = profile_loader or ProfileLoader()

    def _ensure_llm(self):
        if self.llm is None:
            self.llm = get_llm_provider(task="shortlist_reranking")

    async def match_job(self, job: JobRecord, profile: Dict[str, Any]) -> MatchResult:
        """Score an individual job against candidate profile."""
        # 1. Hard filters check
        is_rejected, reason = check_hard_filters(job)
        if is_rejected:
            result = MatchResult(
                job_id=job.job_id,
                match_score=0.0,
                match_status=MatchStatus.NO_MATCH,
                cons=[reason or "Failed hard filter"],
                reasoning=reason or "Excluded by hard filter",
            )
            self._apply_result_to_job(job, result)
            return result

        # 2. Multi-dimension scoring
        comp_score, status, dim_scores, pros, cons, concerns = self.scorer.score_job(job, profile)

        # 3. Determine recommended resume variant
        title_lower = job.title.lower()
        if "automation" in title_lower or "make.com" in title_lower or "flow" in title_lower:
            variant = "ai_automation"
        elif "solutions" in title_lower or "consultant" in title_lower:
            variant = "solutions_engineer"
        elif "data" in title_lower or "analytics" in title_lower:
            variant = "data_analytics"
        else:
            variant = "ai_engineer"

        reasoning_text = (
            f"Role match: {dim_scores.get('role_relevance', 0.0):.2f}, "
            f"Skills: {dim_scores.get('technical_skill', 0.0):.2f}, "
            f"Experience: {dim_scores.get('experience', 0.0):.2f}, "
            f"Location/Remote: {dim_scores.get('location_remote', 0.0):.2f}."
        )

        result = MatchResult(
            job_id=job.job_id,
            match_score=comp_score,
            match_status=status,
            dimension_scores=dim_scores,
            pros=pros,
            cons=cons,
            concerns=concerns,
            recommended_variant=variant,
            optimizer_recommended=len(concerns) > 0 or comp_score >= 0.70,
            reasoning=reasoning_text,
        )

        self._apply_result_to_job(job, result)
        return result

    async def match_batch(self, jobs: List[JobRecord]) -> List[MatchResult]:
        """
        Run 2-stage matching over a batch of jobs:
        Stage 1: Fast embedding pre-ranking.
        Stage 2: Thorough dimension scoring and classification.
        """
        if not jobs:
            return []

        profile = self.profile_loader.load()
        profile_text = self.embedder.build_profile_text(profile)

        # Stage 1: Bulk Embedding Pre-ranking
        ranked_pairs = await self.embedder.rank_jobs(profile_text, jobs, top_n=self.top_n)
        top_jobs = [pair[0] for pair in ranked_pairs]

        # Stage 2: Dimension Scoring
        results: List[MatchResult] = []
        for job in top_jobs:
            mr = await self.match_job(job, profile)
            results.append(mr)

        # Sort results descending by score
        results.sort(key=lambda r: r.match_score, reverse=True)
        return results

    def _apply_result_to_job(self, job: JobRecord, result: MatchResult):
        job.match_score = result.match_score
        job.match_status = result.match_status
        job.recommended_resume = result.recommended_variant
        job.match_reasoning = {
            "dimensions": result.dimension_scores,
            "pros": result.pros,
            "cons": result.cons,
            "concerns": result.concerns,
            "reasoning": result.reasoning,
        }

    async def run(self, input_data: Any) -> Any:
        if isinstance(input_data, JobRecord):
            profile = self.profile_loader.load()
            return await self.match_job(input_data, profile)
        elif isinstance(input_data, list):
            return await self.match_batch(input_data)
        return []
