"""Render a structured CV / cover letter to LaTeX + PDF.

The escape -> LaTeX -> compile -> base64 pipeline used to be copy-pasted into the
generation pipeline, the manual-edit route, and the saved-document PDF routes.
It lives here now so there is exactly one path from structured data to a PDF.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEFAULT_TEMPLATE_SLUG
from app.models import Template, User
from app.schemas import CoverLetter, CurriculumVitae
from app.services.latex import (
    compile_latex_to_pdf,
    cover_letter_to_latex,
    cv_to_latex,
)
from app.services.latex_escape import (
    escape_cover_letter_for_latex,
    escape_cv_for_latex,
)

logger = logging.getLogger(__name__)


@dataclass
class Rendered:
    """Result of rendering a document: the LaTeX source plus its compilation."""

    latex: str
    success: bool
    page_count: int
    pdf_bytes: bytes | None
    error: str | None

    @property
    def pdf_base64(self) -> str:
        """Base64 PDF, or empty string when compilation produced no bytes."""
        return base64.b64encode(self.pdf_bytes).decode() if self.pdf_bytes else ""


def _compile(latex: str, label: str) -> Rendered:
    compiled = compile_latex_to_pdf(latex)
    if not compiled.success:
        logger.error("%s compilation failed: %s", label, compiled.error)
    return Rendered(
        latex=latex,
        success=compiled.success,
        page_count=compiled.page_count,
        pdf_bytes=compiled.pdf_bytes,
        error=compiled.error,
    )


def render_cv(cv: CurriculumVitae, template_slug: str = DEFAULT_TEMPLATE_SLUG) -> Rendered:
    return _compile(cv_to_latex(escape_cv_for_latex(cv), template_slug), "CV")


def render_cover_letter(cl: CoverLetter) -> Rendered:
    return _compile(cover_letter_to_latex(escape_cover_letter_for_latex(cl)), "Cover-letter")


def resolve_template_slug(
    db: Session, user: User | None, template_id: UUID | str | None = None
) -> str:
    """Pick the template slug: an explicit ``template_id`` wins, then the user's
    preferred template, else the default. Unknown ids fall through silently."""
    for candidate in (template_id, user.preferred_template_id if user else None):
        if not candidate:
            continue
        tmpl = db.scalar(select(Template).where(Template.id == candidate))
        if tmpl:
            return tmpl.slug
    return DEFAULT_TEMPLATE_SLUG
