"""
Feedback Loop for Match Calibration.
Allows user thumbs up/down feedback to adaptively calibrate dimension weights
within safe bounds (0.05 <= weight <= 0.40).
"""

from typing import Any, Dict, Optional
from jobpilot.database.repository import Repository


MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.40
DELTA_STEP = 0.02


class FeedbackLoop:
    """Processes user thumbs up/down interactions to calibrate scoring weights."""

    def __init__(self, repo: Optional[Repository] = None):
        self.repo = repo or Repository()

    def record_feedback(self, job_id: str, feedback: str, current_weights: Dict[str, float]) -> Dict[str, float]:
        """
        Record feedback and compute weight delta.
        feedback: 'THUMBS_UP' or 'THUMBS_DOWN'
        Returns updated weights.
        """
        job = self.repo.get_job(job_id)
        if not job:
            return current_weights

        weight_delta: Dict[str, float] = {}
        new_weights = dict(current_weights)

        # Parse job dimensions
        dimensions = {}
        if job.match_reasoning:
            import json
            try:
                data = json.loads(job.match_reasoning) if isinstance(job.match_reasoning, str) else job.match_reasoning
                dimensions = data.get("dimensions", {})
            except Exception:
                pass

        if feedback == "THUMBS_UP":
            # Strengthen dimensions where this job was particularly strong
            for dim, score in dimensions.items():
                if score >= 0.80 and dim in new_weights:
                    delta = DELTA_STEP
                    new_weights[dim] = min(MAX_WEIGHT, round(new_weights[dim] + delta, 3))
                    weight_delta[dim] = delta
        elif feedback == "THUMBS_DOWN":
            # Weaken dimensions where this job scored deceptively high
            for dim, score in dimensions.items():
                if score >= 0.70 and dim in new_weights:
                    delta = -DELTA_STEP
                    new_weights[dim] = max(MIN_WEIGHT, round(new_weights[dim] + delta, 3))
                    weight_delta[dim] = delta

        # Normalize weights to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: round(v / total, 3) for k, v in new_weights.items()}

        # Save to match_feedback table
        self.repo.save_feedback(job_id, feedback, weight_delta)
        # Update job record with feedback
        self.repo.upsert_job({"job_id": job_id, "user_feedback": feedback})

        return new_weights
