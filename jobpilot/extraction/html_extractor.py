"""
HTML Extractor for Job Postings.
Extracts title, company, location, requirements, and full text from arbitrary HTML job pages.
Combines with normalizer to output clean JobRecord models.
"""

from typing import Optional
from bs4 import BeautifulSoup
import re

from jobpilot.core.schemas import JobRecord, RemotePolicy, EmploymentType
from jobpilot.extraction.normalizer import parse_salary, parse_experience, extract_skills
from jobpilot.database.models import utcnow_str
from jobpilot.discovery.deduplicator import compute_url_hash


class HTMLExtractor:
    """Parses raw HTML job postings into structured JobRecords."""

    def extract(self, html: str, url: str, source: str = "web_html") -> Optional[JobRecord]:
        if not html or not html.strip():
            return None

        soup = BeautifulSoup(html, "lxml")

        # Strip scripts, styles, navigations, footers, headers
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "svg"]):
            tag.decompose()

        # 1. Title extraction
        title = self._extract_title(soup)
        if not title:
            title = "Untitled Job Opening"

        # 2. Company extraction
        company = self._extract_company(soup, url)

        # 3. Description extraction
        description = self._extract_description(soup)

        # 4. Location and Remote Policy
        location = self._extract_location(soup, description)
        remote_policy = self._detect_remote(title, description, location)

        # 5. Salary, experience, skills
        salary_min, salary_max, currency = parse_salary(description)
        exp_min, exp_max = parse_experience(description)
        skills = extract_skills(description)

        # 6. Country detection
        country = self._detect_country(location, description)

        job_id = f"job_{compute_url_hash(url)[:24]}"

        return JobRecord(
            job_id=job_id,
            company=company,
            title=title,
            description=description,
            location=location,
            country=country,
            remote_policy=remote_policy,
            employment_type=EmploymentType.FULL_TIME,
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            experience_min=exp_min,
            experience_max=exp_max,
            skills=skills,
            job_url=url,
            source=source,
            date_found=utcnow_str(),
            quality_score=0.90,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        # Try meta tags
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try h1
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text(strip=True)
            if len(text) > 3 and len(text) < 120:
                return text

        # Try page title tag
        if soup.title and soup.title.string:
            title_text = soup.title.string.strip()
            # Clean common title endings
            title_text = re.sub(r"\s*[-|–—]\s*(Careers|Jobs|Greenhouse|Lever|Workday).*", "", title_text, flags=re.IGNORECASE)
            return title_text

        return ""

    def _extract_company(self, soup: BeautifulSoup, url: str) -> str:
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            return og_site["content"].strip()

        # Try JSON-LD Schema.org JobPosting
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string or "{}")
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    org = data.get("hiringOrganization", {})
                    if isinstance(org, dict) and org.get("name"):
                        return org["name"].strip()
            except Exception:
                pass

        # Heuristic from domain
        from urllib.parse import urlparse
        netloc = urlparse(url).netloc
        parts = netloc.split(".")
        if len(parts) >= 2:
            return parts[-2].capitalize()
        return "Unknown Company"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        # Check standard container classes
        candidates = soup.find_all(["div", "section", "article", "main"], class_=re.compile(r"(job-description|description|posting-content|content|details|body)", re.IGNORECASE))
        if candidates:
            # Pick the largest text container
            best = max(candidates, key=lambda c: len(c.get_text()))
            text = best.get_text(separator="\n", strip=True)
            if len(text) > 100:
                return text

        # Fallback to body text
        if soup.body:
            return soup.body.get_text(separator="\n", strip=True)
        return soup.get_text(separator="\n", strip=True)

    def _extract_location(self, soup: BeautifulSoup, description: str) -> Optional[str]:
        # Check for location in meta or specific classes
        loc_el = soup.find(class_=re.compile(r"location|workplace", re.IGNORECASE))
        if loc_el:
            return loc_el.get_text(strip=True)

        for country in ["India", "Germany", "Netherlands", "United Kingdom", "UK", "Canada", "Australia", "Singapore", "UAE"]:
            if country.lower() in description[:300].lower():
                return country
        return None

    def _detect_remote(self, title: str, description: str, location: Optional[str]) -> RemotePolicy:
        combined = f"{title} {description[:400]} {location or ''}".lower()
        if "remote" in combined or "work from home" in combined or "telecommute" in combined:
            return RemotePolicy.REMOTE
        elif "hybrid" in combined:
            return RemotePolicy.HYBRID
        elif "on-site" in combined or "onsite" in combined:
            return RemotePolicy.ONSITE
        return RemotePolicy.UNKNOWN

    def _detect_country(self, location: Optional[str], description: str) -> Optional[str]:
        text = f"{location or ''} {description[:500]}".lower()
        mapping = {
            "india": "India",
            "mumbai": "India",
            "bengaluru": "India",
            "bangalore": "India",
            "germany": "Germany",
            "berlin": "Germany",
            "munich": "Germany",
            "netherlands": "Netherlands",
            "amsterdam": "Netherlands",
            "united kingdom": "UK",
            "uk": "UK",
            "london": "UK",
            "canada": "Canada",
            "toronto": "Canada",
            "vancouver": "Canada",
            "australia": "Australia",
            "sydney": "Australia",
            "melbourne": "Australia",
            "singapore": "Singapore",
            "uae": "UAE",
            "dubai": "UAE",
        }
        for token, country in mapping.items():
            if re.search(r"\b" + re.escape(token) + r"\b", text):
                return country
        return None
