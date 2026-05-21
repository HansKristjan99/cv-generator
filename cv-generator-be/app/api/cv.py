"""`/cv/generate/` route — queue a generation job. Orchestration lives in services.generation_pipeline."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import (
    MAX_CV_TEXT_CHARS,
    MAX_FILE_SIZE_BYTES,
    MAX_JOB_DESCRIPTION_CHARS,
    MAX_MESSAGES_PER_SESSION,
    MAX_SESSIONS_PER_MONTH,
    MAX_USER_MESSAGE_CHARS,
)
from app.db import get_db
from app.models import CvSession, Message, Template, User
from app.services.auth import ensure_current_user
from app.services.generation_pipeline import run_pipeline
from app.services.user_data import format_user_data

router = APIRouter(prefix="/cv", tags=["cv"])
logger = logging.getLogger(__name__)


def _month_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _check_session_available(user: User, db: Session) -> None:
    if user.is_unlimited:
        return
    count = db.scalar(
        select(func.count(CvSession.id)).where(
            CvSession.user_id == user.id, CvSession.created_at >= _month_start(),
        )
    ) or 0
    if count >= MAX_SESSIONS_PER_MONTH:
        raise HTTPException(429, f"Monthly limit of {MAX_SESSIONS_PER_MONTH} CV sessions reached.")


def _get_session(session_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> CvSession:
    session = db.scalar(
        select(CvSession).where(
            CvSession.id == session_id, CvSession.user_id == user_id,
        )
    )
    if session is None:
        raise HTTPException(404, "Unknown or expired conversation.")
    return session


def _resolve_template_slug(template_id: str | None, user: User, db: Session) -> str:
    if template_id:
        tmpl = db.query(Template).filter(Template.id == template_id).first()
        if tmpl:
            return tmpl.slug
    if user.preferred_template_id:
        tmpl = db.query(Template).filter(Template.id == user.preferred_template_id).first()
        if tmpl:
            return tmpl.slug
    return "default"


class StartGenerateResponse(BaseModel):
    session_id: str
    status: str


@router.post("/generate/", response_model=StartGenerateResponse, status_code=202)
async def generate_cv(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(ensure_current_user)],
    db: Annotated[Session, Depends(get_db)],
    user_message: str | None = Form(None),
    text: str | None = Form(None),
    job_description: str | None = Form(None),
    file: UploadFile | None = File(None),
    session_id: uuid.UUID | None = Form(None),
    template_id: str | None = Form(None),
) -> StartGenerateResponse:
    file_path: Path | None = None
    logger.info(
        "generate_cv user=%s session_id=%s has_text=%s has_file=%s has_jd=%s template_id=%s",
        current_user.id, session_id, bool(text), file is not None, bool(job_description), template_id,
    )

    if session_id is None:
        if not (text or file) or not job_description:
            raise HTTPException(400, "Provide CV (text or file) and a job description on first turn.")
        if text and len(text) > MAX_CV_TEXT_CHARS:
            raise HTTPException(413, f"CV text exceeds {MAX_CV_TEXT_CHARS:,} character limit.")
        if job_description and len(job_description) > MAX_JOB_DESCRIPTION_CHARS:
            raise HTTPException(413, f"Job description exceeds {MAX_JOB_DESCRIPTION_CHARS:,} character limit.")
        if user_message and len(user_message) > MAX_USER_MESSAGE_CHARS:
            raise HTTPException(413, f"Message exceeds {MAX_USER_MESSAGE_CHARS:,} character limit.")

        _check_session_available(current_user, db)
        if file is not None:
            file_bytes = await file.read()
            if len(file_bytes) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit.")
            with NamedTemporaryFile(delete=False, suffix=Path(file.filename or "").suffix) as tmp:
                tmp.write(file_bytes)
                file_path = Path(tmp.name)

        cv_session = CvSession(
            user_id=current_user.id,
            conversation_id=f"pending-{uuid.uuid4()}",
            job_description=job_description,
            message_count=1,
            status="pending",
        )

        prompt_input = (
            f"=== CANDIDATE'S STORED PROFILE ===\n{format_user_data(db, current_user.id)}\n\n"
            f"=== SOURCE TEXT ===\n{text or '(none provided)'}\n\n"
            f"=== JOB DESCRIPTION ===\n{job_description}\n\n"
            f"=== USER MESSAGE ===\n{user_message or 'Help me write a CV tailored to this job.'}"
        )
        openai_conversation_id = None
        user_message_text = user_message or "Help me write a CV tailored to this job."
    else:
        if not user_message:
            raise HTTPException(400, "user_message is required on follow-up turns.")
        if len(user_message) > MAX_USER_MESSAGE_CHARS:
            raise HTTPException(413, f"Message exceeds {MAX_USER_MESSAGE_CHARS:,} character limit.")

        cv_session = _get_session(session_id, current_user.id, db)
        if cv_session.status in {"pending", "running"}:
            raise HTTPException(409, "Conversation is still generating.")
        if cv_session.conversation_id.startswith("pending-"):
            raise HTTPException(409, "Conversation is not ready for follow-up messages.")
        if not current_user.is_unlimited and cv_session.message_count >= MAX_MESSAGES_PER_SESSION:
            raise HTTPException(429, f"Conversation limit of {MAX_MESSAGES_PER_SESSION} messages reached.")
        cv_session.message_count += 1
        cv_session.status = "pending"
        cv_session.error = None

        prompt_input = user_message
        openai_conversation_id = cv_session.conversation_id
        user_message_text = user_message
        job_description = cv_session.job_description
        text = None

    template_slug = _resolve_template_slug(template_id, current_user, db)
    cv_session.status = "pending"
    cv_session.error = None
    db.add(cv_session)
    db.flush()
    db.add(Message(
        cv_session_id=cv_session.id,
        role="user",
        content={"role": "user", "type": "text", "content": user_message_text},
    ))
    db.commit()

    background_tasks.add_task(
        run_pipeline,
        cv_session_id=cv_session.id,
        user_id=current_user.id,
        prompt_input=prompt_input,
        openai_conversation_id=openai_conversation_id,
        template_slug=template_slug,
        file_path=file_path,
        user_message_text=user_message_text,
        job_description=job_description,
        cv_text=text,
    )

    logger.info("generate_cv queued session=%s", cv_session.id)
    return StartGenerateResponse(
        session_id=str(cv_session.id),
        status=cv_session.status,
    )
