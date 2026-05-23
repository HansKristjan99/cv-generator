"""Manual-edit endpoint: accept edited structured CV/CL, re-render PDF, persist as new message."""

import base64
import logging
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CvSession, Message
from app.schemas import CoverLetter, CurriculumVitae
from app.services.auth import CurrentUser
from app.services.latex import compile_latex_to_pdf, cover_letter_to_latex, cv_to_latex
from app.services.latex_escape import escape_cover_letter_for_latex, escape_cv_for_latex

router = APIRouter(prefix="/cv", tags=["cv"])
logger = logging.getLogger(__name__)


class ManualEditRequest(BaseModel):
    kind: Literal["cv", "cover_letter"]
    data: dict


class ManualEditResponse(BaseModel):
    pdf_base64: str


@router.patch("/sessions/{session_id}/edit", response_model=ManualEditResponse)
def manual_edit(
    session_id: uuid.UUID,
    body: ManualEditRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ManualEditResponse:
    cv_session = db.scalar(
        select(CvSession).where(
            CvSession.id == session_id, CvSession.user_id == current_user.id,
        )
    )
    if cv_session is None:
        raise HTTPException(404, "Conversation not found.")
    if cv_session.status in {"pending", "running"}:
        raise HTTPException(409, "Conversation is still generating; wait before editing.")

    try:
        if body.kind == "cv":
            structured = CurriculumVitae.model_validate(body.data)
            escaped = escape_cv_for_latex(structured)
            template_slug = _resolve_template_slug(cv_session, db)
            latex = cv_to_latex(escaped, template_slug)
        else:
            structured = CoverLetter.model_validate(body.data)
            escaped = escape_cover_letter_for_latex(structured)
            latex = cover_letter_to_latex(escaped)
    except ValidationError as exc:
        raise HTTPException(422, f"Invalid document structure: {exc}") from exc

    compiled = compile_latex_to_pdf(latex)
    if not compiled.success or not compiled.pdf_bytes:
        logger.error("Manual-edit PDF compilation failed: %s", compiled.error)
        raise HTTPException(500, "PDF compilation failed; check the edited fields for invalid characters.")

    pdf_b64 = base64.b64encode(compiled.pdf_bytes).decode()

    msg_type = "cv" if body.kind == "cv" else "cover_letter"
    db.add(Message(
        cv_session_id=cv_session.id,
        role="assistant",
        content={
            "role": "assistant",
            "type": msg_type,
            "content": latex,
            "pdf_base64": pdf_b64,
            "structured_data": body.data,
            "source": "manual_edit",
        },
    ))
    db.commit()
    logger.info("manual_edit session=%s kind=%s", session_id, body.kind)
    return ManualEditResponse(pdf_base64=pdf_b64)


def _resolve_template_slug(cv_session: CvSession, db: Session) -> str:
    from app.models import Template
    if cv_session.user_id:
        from app.models import User
        user = db.get(User, cv_session.user_id)
        if user and user.preferred_template_id:
            tmpl = db.get(Template, user.preferred_template_id)
            if tmpl:
                return tmpl.slug
    return "default"
