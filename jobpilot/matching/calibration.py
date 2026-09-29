"""
Calibration Test Set Evaluator for JobPilot AI.
Computes precision, recall, and F1 score against manually labeled job examples.
"""

from typing import Any, Dict, List
from jobpilot.core.schemas import MatchStatus, JobRecord
from jobpilot.matching.engine import MatchingEngine


class MatchCalibrator:
    """Measures accuracy and alignment against labeled benchmark sets."""

    def __init__(self, engine: MatchingEngine):
        self.engine = engine

    async def evaluate_labeled_set(self, labeled_jobs: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        labeled_jobs: List of dicts with keys: 'job' (JobRecord) and 'expected_label' ('GOOD' or 'BAD').
        Threshold for positive match is MatchStatus.STRONG_MATCH or MatchStatus.GOOD_MATCH.
        """
        tp = 0
        fp = 0
        fn = 0
        tn = 0

        for item in labeled_jobs:
            job: JobRecord = item["job"]
            expected = item["expected_label"].upper()

            res = await self.engine.run(job)
            predicted_good = res.match_status in (MatchStatus.STRONG_MATCH, MatchStatus.GOOD_MATCH)

            if predicted_good and expected == "GOOD":
                tp += 1
            elif predicted_good and expected == "BAD":
                fp += 1
            elif not predicted_good and expected == "GOOD":
                fn += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / len(labeled_jobs) if labeled_jobs else 0.0

        return {
            "total_evaluated": len(labeled_jobs),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1, 3),
            "accuracy": round(accuracy, 3),
        }
