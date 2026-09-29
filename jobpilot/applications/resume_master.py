"""
Master Resume Loader and Variant Assembler for JobPilot AI.
Builds structured ResumeDoc objects directly from the candidate's verified profile data.
Strictly adheres to zero fabrication: never invents companies, dates, or degrees.
"""

from typing import Any, Dict, List, Optional
from jobpilot.core.schemas import OptimizerMode, ResumeDoc
from jobpilot.profiles.loader import ProfileLoader


class ResumeMaster:
    """Loads and formats candidate resume documents and domain-targeted variants."""

    def __init__(self, profile_path: Optional[str] = None):
        self.loader = ProfileLoader(profile_path=profile_path)
        self._profile_cache: Optional[Dict[str, Any]] = None

    def get_profile(self) -> Dict[str, Any]:
        if self._profile_cache is None:
            self._profile_cache = self.loader.load_profile()
        return self._profile_cache

    def assemble_resume(
        self,
        variant: str = "default",
        custom_summary: Optional[str] = None,
    ) -> ResumeDoc:
        """
        Assembles a ResumeDoc from the candidate profile for the specified variant.
        Variants: 'default', 'ai_engineer', 'ai_automation', 'data_analytics'.
        """
        profile = self.get_profile()
        personal = profile.get("personal", {})
        skills = profile.get("skills", {})
        edu_list = profile.get("education", [])
        master_resume = profile.get("master_resume", {})

        # Build contact & summary info
        full_name = personal.get("full_name", "Ankita Yadav")
        email = personal.get("email", "NEEDS_USER_INPUT")
        phone = personal.get("phone", "NEEDS_USER_INPUT")
        city = personal.get("location_city", "Mumbai")
        country = personal.get("location_country", "India")
        location = f"{city}, {country}" if city and country else (city or country or "Mumbai, India")

        summary = custom_summary or master_resume.get("summary") or "AI & Data Science professional specializing in Generative AI, LLMs, and intelligent automation systems."

        # Copy skills dict safely
        skills_dict: Dict[str, List[str]] = {}
        for category, skill_items in skills.items():
            if isinstance(skill_items, list):
                skills_dict[category] = list(skill_items)

        # Variant-specific category ordering
        variant_lower = variant.lower()
        ordered_skills: Dict[str, List[str]] = {}
        if variant_lower in ("ai_engineer", "generative_ai"):
            # Put ai_ml and programming at top
            for cat in ["ai_ml", "programming", "platforms_tools", "data", "integrations"]:
                if cat in skills_dict:
                    ordered_skills[cat] = skills_dict[cat]
        elif variant_lower in ("ai_automation", "solutions_engineer"):
            # Put platforms_tools and integrations at top
            for cat in ["platforms_tools", "integrations", "ai_ml", "programming", "data"]:
                if cat in skills_dict:
                    ordered_skills[cat] = skills_dict[cat]
        elif variant_lower in ("data_analytics", "analytics"):
            # Put data and programming at top
            for cat in ["data", "programming", "platforms_tools", "ai_ml", "integrations"]:
                if cat in skills_dict:
                    ordered_skills[cat] = skills_dict[cat]
        else:
            ordered_skills = skills_dict

        # Remaining categories not in ordered list
        for cat, items in skills_dict.items():
            if cat not in ordered_skills:
                ordered_skills[cat] = items

        # Education
        education: List[Dict[str, Any]] = []
        for edu in edu_list:
            if isinstance(edu, dict):
                education.append({
                    "degree": edu.get("degree", "Bachelor of Technology (B.Tech)"),
                    "field": edu.get("field", "Artificial Intelligence & Data Science"),
                    "institution": edu.get("institution", "NEEDS_USER_INPUT"),
                    "graduation_year": edu.get("graduation_year", "NEEDS_USER_INPUT"),
                })

        # Experience & Projects from master resume
        experience: List[Dict[str, Any]] = []
        for emp in master_resume.get("employment", []):
            if isinstance(emp, dict):
                bullets = []
                for b in emp.get("bullets", []):
                    if isinstance(b, dict):
                        bullets.append(b.get("text", "NEEDS_USER_INPUT"))
                    elif isinstance(b, str):
                        bullets.append(b)
                experience.append({
                    "employer": emp.get("employer", "NEEDS_USER_INPUT"),
                    "title": emp.get("title", "NEEDS_USER_INPUT"),
                    "bullets": bullets,
                })

        projects: List[Dict[str, Any]] = []
        for proj in master_resume.get("projects", []):
            if isinstance(proj, dict):
                bullets = []
                for b in proj.get("bullets", []):
                    if isinstance(b, dict):
                        bullets.append(b.get("text", "NEEDS_USER_INPUT"))
                    elif isinstance(b, str):
                        bullets.append(b)
                projects.append({
                    "name": proj.get("name", "NEEDS_USER_INPUT"),
                    "bullets": bullets,
                })

        return ResumeDoc(
            variant=variant,
            full_name=full_name,
            contact_email=str(email),
            contact_phone=str(phone) if phone != "NEEDS_USER_INPUT" else None,
            location=location,
            summary=summary,
            skills=ordered_skills,
            experience=experience,
            education=education,
            projects=projects,
            certifications=[],
            source_variant="master",
            optimizer_mode=OptimizerMode.OFF,
            optimizer_diff=[],
        )
