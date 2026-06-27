"""Manual-edit endpoint: accept edited structured CV/CL, re-render PDF, persist as new message."""

import logging
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Message
from app.schemas import CoverLetter, CurriculumVitae
from app.services.auth import CurrentUser
from app.services.rendering import render_cover_letter, render_cv, resolve_template_slug
from app.services.sessions import get_user_session

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
    cv_session = get_user_session(db, session_id, current_user.id)
    if cv_session.status in {"pending", "running"}:
        raise HTTPException(409, "Conversation is still generating; wait before editing.")

    try:
        if body.kind == "cv":
            structured = CurriculumVitae.model_validate(body.data)
            rendered = render_cv(structured, resolve_template_slug(db, current_user))
        else:
            structured = CoverLetter.model_validate(body.data)
            rendered = render_cover_letter(structured)
    except ValidationError as exc:
        raise HTTPException(422, f"Invalid document structure: {exc}") from exc

    if not rendered.success or not rendered.pdf_bytes:
        logger.error("Manual-edit PDF compilation failed: %s", rendered.error)
        raise HTTPException(500, "PDF compilation failed; check the edited fields for invalid characters.")

    db.add(Message(
        cv_session_id=cv_session.id,
        role="assistant",
        content={
            "role": "assistant",
            "type": body.kind,
            "content": rendered.latex,
            "pdf_base64": rendered.pdf_base64,
            "structured_data": body.data,
            "source": "manual_edit",
        },
    ))
    db.commit()
    logger.info("manual_edit session=%s kind=%s", session_id, body.kind)
    return ManualEditResponse(pdf_base64=rendered.pdf_base64)
