"""Compile and cache PDFs for persisted CV / cover-letter snapshots.

A saved ``Cv``/``Cl`` row stores structured data (the source of truth) and an
optional cached ``pdf_base64``. These helpers render the PDF on first request,
cache it on the row, and return it.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Cl, Cv
from app.schemas import CoverLetter, CurriculumVitae
from app.services.rendering import render_cover_letter, render_cv, resolve_template_slug

logger = logging.getLogger(__name__)


def compile_cv_pdf(db: Session, cv: Cv) -> str:
    """Render a saved CV to PDF (base64), cache it on the row, and return it."""
    try:
        structured = CurriculumVitae.model_validate(cv.structured_data)
    except ValidationError as exc:
        raise HTTPException(422, f"Stored CV is malformed: {exc}") from exc
    rendered = render_cv(structured, resolve_template_slug(db, None, cv.template_id))
    if not rendered.success or not rendered.pdf_bytes:
        logger.error("CV %s PDF compile failed: %s", cv.id, rendered.error)
        raise HTTPException(500, "PDF compilation failed.")
    cv.pdf_base64 = rendered.pdf_base64
    db.commit()
    return cv.pdf_base64


def compile_cl_pdf(db: Session, cl: Cl) -> str:
    try:
        structured = CoverLetter.model_validate(cl.structured_data)
    except ValidationError as exc:
        raise HTTPException(422, f"Stored cover letter is malformed: {exc}") from exc
    rendered = render_cover_letter(structured)
    if not rendered.success or not rendered.pdf_bytes:
        logger.error("CL %s PDF compile failed: %s", cl.id, rendered.error)
        raise HTTPException(500, "PDF compilation failed.")
    cl.pdf_base64 = rendered.pdf_base64
    db.commit()
    return cl.pdf_base64
