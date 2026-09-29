"""
Truthful Resume Optimizer for JobPilot AI.
Supports three operating modes: OFF, SUGGEST, and AUTO.
Guarantees zero hallucination and zero fabrication:
Only existing verified skills and bullets are prioritized or reordered.
Never invents claims, tools, or metrics.
"""

import copy
from typing import Any, Dict, List, Optional
from jobpilot.core.safety import assert_optimizer_no_new_claims
from jobpilot.core.schemas import JobRecord, OptimizerMode, ResumeDoc


class ResumeOptimizer:
    """
    Optimizes a ResumeDoc for a specific target JobRecord.
    Maintains strict truthfulness by only reordering verified content.
    """

    def __init__(self, mode: OptimizerMode = OptimizerMode.OFF):
        self.mode = mode

    def optimize(
        self,
        resume: ResumeDoc,
        job: JobRecord,
        mode_override: Optional[OptimizerMode] = None,
    ) -> ResumeDoc:
        """
        Optimizes the resume according to the selected mode.
        """
        active_mode = mode_override or self.mode

        if active_mode == OptimizerMode.OFF:
            res = copy.deepcopy(resume)
            res.optimizer_mode = OptimizerMode.OFF
            res.optimizer_diff = []
            return res

        job_skills = set(s.lower().strip() for s in (job.skills or []))
        diff_log: List[str] = []

        if active_mode == OptimizerMode.SUGGEST:
            res = copy.deepcopy(resume)
            res.optimizer_mode = OptimizerMode.SUGGEST

            # Find matching skills in candidate profile
            matching_skills = []
            for cat, skills_list in res.skills.items():
                for s in skills_list:
                    if s.lower().strip() in job_skills:
                        matching_skills.append(s)

            if matching_skills:
                diff_log.append(f"SUGGESTION: Prioritize matching verified skills in header: {matching_skills}")
            else:
                diff_log.append("SUGGESTION: Emphasize core Python and AI engineering capabilities.")

            # Suggest highlighting relevant projects/bullets
            for idx, proj in enumerate(res.projects):
                proj_name = proj.get("name", f"Project {idx+1}")
                diff_log.append(f"SUGGESTION: Highlight {proj_name} relevance to {job.title} at {job.company}.")

            res.optimizer_diff = diff_log
            return res

        elif active_mode == OptimizerMode.AUTO:
            res = copy.deepcopy(resume)
            res.optimizer_mode = OptimizerMode.AUTO

            # Reorder skills within each category: target job skills first, then rest
            optimized_skills: Dict[str, List[str]] = {}
            for cat, skills_list in res.skills.items():
                matched: List[str] = []
                unmatched: List[str] = []
                for s in skills_list:
                    if s.lower().strip() in job_skills:
                        matched.append(s)
                    else:
                        unmatched.append(s)
                if matched:
                    diff_log.append(f"REORDERED SKILLS [{cat}]: Promoted {matched} to top of category.")
                optimized_skills[cat] = matched + unmatched
            res.skills = optimized_skills

            # Reorder project bullets by relevance
            for proj in res.projects:
                bullets = proj.get("bullets", [])
                if bullets:
                    high_priority: List[str] = []
                    normal_priority: List[str] = []
                    for b in bullets:
                        b_lower = b.lower()
                        if any(js in b_lower for js in job_skills):
                            high_priority.append(b)
                        else:
                            normal_priority.append(b)
                    if high_priority and high_priority != bullets:
                        diff_log.append(f"REORDERED BULLETS in project '{proj.get('name')}': Prioritized {len(high_priority)} relevant achievement(s).")
                    proj["bullets"] = high_priority + normal_priority

            # Reorder experience bullets by relevance
            for exp in res.experience:
                bullets = exp.get("bullets", [])
                if bullets:
                    high_priority = []
                    normal_priority = []
                    for b in bullets:
                        b_lower = b.lower()
                        if any(js in b_lower for js in job_skills):
                            high_priority.append(b)
                        else:
                            normal_priority.append(b)
                    if high_priority and high_priority != bullets:
                        diff_log.append(f"REORDERED BULLETS in role at '{exp.get('employer')}': Prioritized {len(high_priority)} relevant item(s).")
                    exp["bullets"] = high_priority + normal_priority

            res.optimizer_diff = diff_log

            # Strict Safety Check: Verify no new claims were introduced
            assert_optimizer_no_new_claims(resume, res)

            return res

        else:
            return copy.deepcopy(resume)
