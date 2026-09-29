"""
Extraction and Normalization Engine for JobPostings.
Cleans raw text, parses compensation (INR/USD/EUR/GBP), extracts required experience,
and maps unstructured data into conforming JobRecord models.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from jobpilot.core.schemas import RemotePolicy, EmploymentType


def parse_salary(text: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Extract minimum salary, maximum salary, and currency from job text.
    Handles INR Lakhs/LPA, USD (k/$), EUR, GBP, and range expressions.
    Never guesses: unmentioned or vague compensation returns (None, None, None).
    """
    if not text:
        return None, None, None

    text_clean = text.replace(",", "").strip()

    # 1. INR: "₹18-25 LPA", "15 Lakhs", "12 LPA", "INR 1800000"
    inr_lpa_match = re.search(r"(?:(?:₹|inr|rs\.?)\s*)?(\d+(?:\.\d+)?)\s*(?:-|to)?\s*(\d+(?:\.\d+)?)?\s*(?:lpa|lakhs?|lac|lacs?)\b", text_clean, re.IGNORECASE)
    if inr_lpa_match:
        val1 = float(inr_lpa_match.group(1)) * 100000
        val2 = float(inr_lpa_match.group(2)) * 100000 if inr_lpa_match.group(2) else val1
        return min(val1, val2), max(val1, val2), "INR"

    inr_num_match = re.search(r"(?:₹|inr)\s*(\d{5,8})\s*(?:-|to)?\s*(\d{5,8})?", text_clean, re.IGNORECASE)
    if inr_num_match:
        val1 = float(inr_num_match.group(1))
        val2 = float(inr_num_match.group(2)) if inr_num_match.group(2) else val1
        return min(val1, val2), max(val1, val2), "INR"

    # 2. USD: "$100k - $140k", "$80,000 - $120,000", "70-90k USD"
    usd_k_match = re.search(r"\$\s*(\d+)(?:\.\d+)?\s*k?\s*(?:-|to)\s*\$?\s*(\d+)(?:\.\d+)?\s*k\s*(?:usd)?", text_clean, re.IGNORECASE)
    if usd_k_match:
        v1 = float(usd_k_match.group(1))
        v2 = float(usd_k_match.group(2))
        v1 = v1 * 1000 if v1 < 1000 else v1
        v2 = v2 * 1000 if v2 < 1000 else v2
        return min(v1, v2), max(v1, v2), "USD"

    usd_num_match = re.search(r"\$\s*(\d{4,7})\s*(?:-|to)?\s*\$?\s*(\d{4,7})?\s*(?:usd)?", text_clean, re.IGNORECASE)
    if usd_num_match:
        v1 = float(usd_num_match.group(1))
        v2 = float(usd_num_match.group(2)) if usd_num_match.group(2) else v1
        return min(v1, v2), max(v1, v2), "USD"

    # 3. EUR: "€50,000 - €70,000", "€60k"
    eur_match = re.search(r"€\s*(\d+)(?:\.\d+)?\s*k?\s*(?:-|to)?\s*€?\s*(\d+)?(?:\.\d+)?\s*k?\s*(?:eur)?", text_clean, re.IGNORECASE)
    if eur_match:
        v1 = float(eur_match.group(1))
        v2 = float(eur_match.group(2)) if eur_match.group(2) else v1
        v1 = v1 * 1000 if v1 < 1000 else v1
        v2 = v2 * 1000 if v2 < 1000 else v2
        return min(v1, v2), max(v1, v2), "EUR"

    # 4. GBP: "£45,000 - £60,000", "£50k"
    gbp_match = re.search(r"£\s*(\d+)(?:\.\d+)?\s*k?\s*(?:-|to)?\s*£?\s*(\d+)?(?:\.\d+)?\s*k?\s*(?:gbp)?", text_clean, re.IGNORECASE)
    if gbp_match:
        v1 = float(gbp_match.group(1))
        v2 = float(gbp_match.group(2)) if gbp_match.group(2) else v1
        v1 = v1 * 1000 if v1 < 1000 else v1
        v2 = v2 * 1000 if v2 < 1000 else v2
        return min(v1, v2), max(v1, v2), "GBP"

    return None, None, None


def parse_experience(text: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract required years of experience from text.
    Handles ranges ('1-3 years', '1 to 2 yrs'), minimums ('2+ years', 'at least 3 years').
    """
    if not text:
        return None, None

    # Range: "1-3 years", "1 to 4 years"
    range_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\+?\s*(?:years?|yrs?)", text, re.IGNORECASE)
    if range_match:
        e1 = int(range_match.group(1))
        e2 = int(range_match.group(2))
        return min(e1, e2), max(e1, e2)

    # Minimum: "2+ years", "at least 3 years", "minimum of 1 year"
    min_match = re.search(r"(?:at least|minimum of|min\.?)\s*(\d+)\+?\s*(?:years?|yrs?)", text, re.IGNORECASE)
    if min_match:
        val = int(min_match.group(1))
        return val, None

    plus_match = re.search(r"(\d+)\+\s*(?:years?|yrs?)", text, re.IGNORECASE)
    if plus_match:
        val = int(plus_match.group(1))
        return val, None

    single_match = re.search(r"(\d+)\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)", text, re.IGNORECASE)
    if single_match:
        val = int(single_match.group(1))
        return val, val

    return None, None


def extract_skills(text: Optional[str]) -> List[str]:
    """Identify relevant technical skills mentioned in the job description."""
    if not text:
        return []

    KNOWN_SKILLS = [
        "python", "javascript", "typescript", "sql", "generative ai", "llm", "llms",
        "rag", "langchain", "llamaindex", "make.com", "power automate", "tableau",
        "power bi", "aws", "docker", "git", "rest api", "rest apis", "webhooks",
        "fastapi", "flask", "django", "pytorch", "tensorflow", "scikit-learn",
        "pandas", "numpy", "agentic ai", "ai agents", "prompt engineering",
        "hugging face", "vector database", "pinecone", "chromadb", "weaviate",
    ]
    text_lower = text.lower()
    found = set()
    for s in KNOWN_SKILLS:
        pattern = r"\b" + re.escape(s) + r"\b"
        if re.search(pattern, text_lower):
            # Display name formatting
            if s in ("python", "javascript", "typescript", "sql", "docker", "git"):
                found.add(s.capitalize() if s != "sql" else "SQL")
            elif s == "llms":
                found.add("LLMs")
            elif s in ("rag", "llm", "aws"):
                found.add(s.upper())
            elif s == "make.com":
                found.add("Make.com")
            elif s == "power automate":
                found.add("Power Automate")
            elif s == "power bi":
                found.add("Power BI")
            elif s == "tableau":
                found.add("Tableau")
            elif s in ("generative ai", "genai"):
                found.add("Generative AI")
            elif s == "rest api" or s == "rest apis":
                found.add("REST APIs")
            elif s == "ai agents" or s == "agentic ai":
                found.add("AI Agents")
            else:
                found.add(s.title())

    return sorted(list(found))
