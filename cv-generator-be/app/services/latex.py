"""Dispatch CV rendering to the correct template and compile to PDF."""

import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.config import (
    DEFAULT_TEMPLATE_SLUG,
    LATEX_COMPILE_ERROR_TAIL_CHARS,
    LATEX_COMPILE_TIMEOUT_SECONDS,
)
from app.schemas import CoverLetter, CurriculumVitae
from app.services.templates import cover_letter, default, harvard_classic, rover

logger = logging.getLogger(__name__)

_RENDERERS: dict[str, Callable[[CurriculumVitae], str]] = {
    "default": default.cv_to_latex,
    "harvard_classic": harvard_classic.cv_to_latex,
    "rover": rover.cv_to_latex,
}


def cv_to_latex(cv: CurriculumVitae, template_slug: str = DEFAULT_TEMPLATE_SLUG) -> str:
    renderer = _RENDERERS.get(template_slug) or _RENDERERS[DEFAULT_TEMPLATE_SLUG]
    return renderer(cv)


def cover_letter_to_latex(cl: CoverLetter) -> str:
    return cover_letter.cover_letter_to_latex(cl)


@dataclass
class CompileResult:
    success: bool
    page_count: int = 0
    pdf_bytes: bytes | None = None
    error: str | None = None


_PAGES_RE = re.compile(r"Output written on .+?\((\d+) pages?")


def compile_latex_to_pdf(
    latex: str,
    timeout: float = LATEX_COMPILE_TIMEOUT_SECONDS,
) -> CompileResult:
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "cv.tex"
        tex_path.write_text(latex)
        try:
            proc = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                 "-output-directory", tmpdir, str(tex_path)],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            logger.error("pdflatex timed out after %.0fs", timeout)
            return CompileResult(success=False, error="pdflatex timed out")
        except FileNotFoundError:
            logger.error("pdflatex binary not found on PATH")
            return CompileResult(success=False, error="pdflatex binary not found on PATH")

        pdf_path = Path(tmpdir) / "cv.pdf"
        if proc.returncode != 0 or not pdf_path.exists():
            tail = (proc.stdout + proc.stderr)[-LATEX_COMPILE_ERROR_TAIL_CHARS:]
            logger.warning("pdflatex compilation failed (returncode=%s)", proc.returncode)
            return CompileResult(success=False, error=tail)

        match = _PAGES_RE.search(proc.stdout)
        page_count = int(match.group(1)) if match else 0
        logger.debug("pdflatex compiled successfully: %d page(s)", page_count)
        return CompileResult(success=True, page_count=page_count, pdf_bytes=pdf_path.read_bytes())
