"""
Document Format Detector for JobPilot AI.
Determines whether target ATS portal requires PDF, DOCX, or TXT.
Defaults to PDF as first choice per user instruction, but dynamically detects explicit ATS requirements.
"""

import re
from typing import List, Optional
from jobpilot.core.schemas import DocumentFormat, JobRecord


class FormatDetector:
    """Detects ATS document format preferences."""

    @staticmethod
    def detect_format(
        job: Optional[JobRecord] = None,
        portal_accept_attr: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> DocumentFormat:
        """
        Determines the optimal document format.
        Priority:
        1. Explicit HTML input 'accept' attribute if single format is strictly mandated (e.g. only .docx).
        2. Explicit text instruction in job posting or application form.
        3. Default to PDF (first choice).
        """
        # 1. Check HTML input accept attribute
        if portal_accept_attr:
            accept_lower = portal_accept_attr.lower()
            # If docx/doc is accepted and PDF is NOT in accept attribute:
            if ("docx" in accept_lower or "word" in accept_lower) and "pdf" not in accept_lower:
                return DocumentFormat.DOCX
            if "txt" in accept_lower and "pdf" not in accept_lower and "doc" not in accept_lower:
                return DocumentFormat.TXT

        # 2. Check custom instructions or job description
        text_corpus = ""
        if custom_instructions:
            text_corpus += " " + custom_instructions
        if job and job.description:
            text_corpus += " " + job.description

        if text_corpus:
            corpus_lower = text_corpus.lower()
            # Check for explicit DOCX/Word requirement
            docx_patterns = [
                r"\b(?:only|must\s+be|require[ds]?)\s+(?:in\s+)?(?:word|\.docx?)\b",
                r"\b(?:upload|submit)\s+(?:in\s+)?(?:word|\.docx?)\s+format\b",
                r"\bdoc(?:x)?\s+(?:only|required)\b",
            ]
            for pat in docx_patterns:
                if re.search(pat, corpus_lower):
                    return DocumentFormat.DOCX

            # Check for plain text requirement
            txt_patterns = [
                r"\b(?:upload|submit|require[ds]?)\s+(?:as\s+)?plain\s+text\b",
                r"\b\.txt\s+(?:only|required)\b",
            ]
            for pat in txt_patterns:
                if re.search(pat, corpus_lower):
                    return DocumentFormat.TXT

        # Default first choice is always PDF
        return DocumentFormat.PDF
