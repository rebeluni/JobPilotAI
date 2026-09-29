"""
Playwright-Powered PDF Document Renderer for JobPilot AI.
Compiles ATS-optimized HTML into pixel-perfect PDF documents using headless Chromium.
Avoids system GTK dependencies (unlike WeasyPrint) for flawless Windows compatibility.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Union
from playwright.async_api import async_playwright

from jobpilot.core.registry import PluginRegistry
from jobpilot.core.schemas import CoverLetterDoc, ResumeDoc
from jobpilot.documents.html_template import render_cover_letter_html, render_resume_html

logger = logging.getLogger(__name__)


def get_default_resumes_dir() -> Path:
    from jobpilot.database.repository import get_data_dir
    p = get_data_dir() / "resumes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_default_cover_letters_dir() -> Path:
    from jobpilot.database.repository import get_data_dir
    p = get_data_dir() / "cover_letters"
    p.mkdir(parents=True, exist_ok=True)
    return p


@PluginRegistry.register_renderer("pdf")
class PDFRenderer:
    """Renders ResumeDoc and CoverLetterDoc into professional PDF documents via Playwright."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else None

    async def render_html_to_pdf_async(
        self,
        html_content: str,
        output_path: Path,
        margin_in: str = "0.5in",
    ) -> Path:
        """Asynchronously renders HTML content to a PDF file using headless Chromium."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser = None
            for channel in ["chrome", "msedge", None]:
                try:
                    kwargs = {"headless": True}
                    if channel:
                        kwargs["channel"] = channel
                    browser = await p.chromium.launch(**kwargs)
                    break
                except Exception:
                    continue

            if not browser:
                raise RuntimeError("No suitable Chromium, Chrome, or Edge executable found for PDF generation.")

            try:
                page = await browser.new_page()
                await page.set_content(html_content, wait_until="networkidle")
                await page.pdf(
                    path=str(output_path),
                    format="A4",
                    print_background=True,
                    margin={
                        "top": margin_in,
                        "bottom": margin_in,
                        "left": margin_in,
                        "right": margin_in,
                    },
                )
                logger.info(f"Rendered PDF to {output_path}")
                return output_path
            finally:
                await browser.close()

    def render_html_to_pdf(self, html_content: str, output_path: Path) -> Path:
        """Synchronous wrapper for PDF rendering."""
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(
                asyncio.run,
                self.render_html_to_pdf_async(html_content, output_path),
            ).result()

    def render_resume(
        self,
        resume: ResumeDoc,
        output_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Renders ResumeDoc to PDF."""
        if not output_path:
            out_dir = self.output_dir or get_default_resumes_dir()
            filename = f"Resume_{resume.full_name.replace(' ', '_')}_{resume.variant}.pdf"
            target_path = out_dir / filename
        else:
            target_path = Path(output_path)

        html = render_resume_html(resume)
        return self.render_html_to_pdf(html, target_path)

    def render_cover_letter(
        self,
        cover_letter: CoverLetterDoc,
        output_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Renders CoverLetterDoc to PDF."""
        if not output_path:
            out_dir = self.output_dir or get_default_cover_letters_dir()
            filename = f"CoverLetter_{cover_letter.company.replace(' ', '_')}_{cover_letter.job_id}.pdf"
            target_path = out_dir / filename
        else:
            target_path = Path(output_path)

        html = render_cover_letter_html(cover_letter)
        return self.render_html_to_pdf(html, target_path)
