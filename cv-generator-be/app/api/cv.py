"""`/cv/generate/` route — queue a generation job. Orchestration lives in services.generation_pipeline."""

import base64
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import (
    COVER_LETTER_TARGET_PAGES,
    CV_PAGE_COUNT_OPTIONS,
    DEFAULT_CV_PAGE_COUNT,
    DEFAULT_TEMPLATE_SLUG,
    INITIAL_SESSION_MESSAGE_COUNT,
    MAX_CV_TEXT_CHARS,
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    MAX_JOB_DESCRIPTION_CHARS,
    MAX_MESSAGES_PER_SESSION,
    MAX_SESSIONS_PER_MONTH,
    MAX_USER_MESSAGE_CHARS,
)
from app.db import get_db
from app.models import CvSession, Message, Template, User
from app.services.auth import ensure_current_user
from app.services.generation_pipeline import run_pipeline
from app.services.subscriptions import has_paid_access
from app.services.user_data import format_user_data

router = APIRouter(prefix="/cv", tags=["cv"])
logger = logging.getLogger(__name__)


def _month_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _check_session_available(user: User, db: Session) -> None:
    if has_paid_access(db, user):
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


def _pdf_to_tempfile(pdf_base64: str) -> Path:
    """Materialize a stored source PDF to a temp file for re-attachment to the agent."""
    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(base64.b64decode(pdf_base64))
        return Path(tmp.name)


def _full_context_prompt(
    db: Session,
    user_id: uuid.UUID,
    *,
    source_text: str | None,
    job_description: str | None,
    message: str,
    message_label: str = "USER MESSAGE",
) -> str:
    """Profile + source + job description + the user's message — the full context used
    on the first turn and again when the user answers the requirements gate."""
    return (
        f"=== CANDIDATE'S STORED PROFILE ===\n{format_user_data(db, user_id)}\n\n"
        f"=== SOURCE TEXT ===\n{source_text or '(none provided)'}\n\n"
        f"=== JOB DESCRIPTION ===\n{job_description}\n\n"
        f"=== {message_label} ===\n{message}"
    )


def _resolve_template_slug(template_id: str | None, user: User, db: Session) -> str:
    if template_id:
        tmpl = db.query(Template).filter(Template.id == template_id).first()
        if tmpl:
            return tmpl.slug
    if user.preferred_template_id:
        tmpl = db.query(Template).filter(Template.id == user.preferred_template_id).first()
        if tmpl:
            return tmpl.slug
    return DEFAULT_TEMPLATE_SLUG


class StartGenerateResponse(BaseModel):
    session_id: str
    status: str


class GenerateForm(BaseModel):
    """Multipart payload for /cv/generate/. New sessions supply the CV source,
    job description, and page count; follow-up turns supply session_id + a message."""

    user_message: str | None = None
    text: str | None = None
    job_description: str | None = None
    file: UploadFile | None = None
    session_id: uuid.UUID | None = None
    template_id: str | None = None
    page_count: int = DEFAULT_CV_PAGE_COUNT
    kind: str = "cv"


@router.post("/generate/", response_model=StartGenerateResponse, status_code=202)
async def generate_cv(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(ensure_current_user)],
    db: Annotated[Session, Depends(get_db)],
    form: Annotated[GenerateForm, Form()],
) -> StartGenerateResponse:
    user_message = form.user_message
    text = form.text
    job_description = form.job_description
    file = form.file
    session_id = form.session_id
    template_id = form.template_id
    page_count = form.page_count
    kind = form.kind

    file_path: Path | None = None
    logger.info(
        "generate_cv user=%s session_id=%s kind=%s has_text=%s has_file=%s has_jd=%s template_id=%s",
        current_user.id, session_id, kind, bool(text), file is not None, bool(job_description), template_id,
    )

    if kind not in ("cv", "cover_letter"):
        raise HTTPException(400, "kind must be 'cv' or 'cover_letter'.")
    # Cover letters always render to one page; page length only applies to CVs.
    if kind == "cover_letter":
        page_count = COVER_LETTER_TARGET_PAGES
    if page_count not in CV_PAGE_COUNT_OPTIONS:
        allowed = ", ".join(str(option) for option in CV_PAGE_COUNT_OPTIONS)
        raise HTTPException(400, f"page_count must be one of: {allowed}.")

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
        source_cv_pdf_base64: str | None = None
        if file is not None:
            file_bytes = await file.read()
            if len(file_bytes) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE_MB} MB limit.")
            with NamedTemporaryFile(delete=False, suffix=Path(file.filename or "").suffix) as tmp:
                tmp.write(file_bytes)
                file_path = Path(tmp.name)
            # Persist the submitted PDF so it can be previewed later in the session.
            if (file.content_type == "application/pdf") or (file.filename or "").lower().endswith(".pdf"):
                source_cv_pdf_base64 = base64.b64encode(file_bytes).decode()

        cv_session = CvSession(
            user_id=current_user.id,
            conversation_id=f"pending-{uuid.uuid4()}",
            job_description=job_description,
            source_cv_text=text or None,
            source_cv_pdf_base64=source_cv_pdf_base64,
            page_count=page_count,
            message_count=INITIAL_SESSION_MESSAGE_COUNT,
            status="pending",
        )

        default_message = (
            "Write a cover letter tailored to this job."
            if kind == "cover_letter"
            else "Help me write a CV tailored to this job."
        )
        prompt_input = _full_context_prompt(
            db, current_user.id,
            source_text=text, job_description=job_description,
            message=user_message or default_message,
        )
        openai_conversation_id = None
        user_message_text = user_message or default_message
    else:
        if not user_message:
            raise HTTPException(400, "user_message is required on follow-up turns.")
        if len(user_message) > MAX_USER_MESSAGE_CHARS:
            raise HTTPException(413, f"Message exceeds {MAX_USER_MESSAGE_CHARS:,} character limit.")

        cv_session = _get_session(session_id, current_user.id, db)
        if cv_session.status in {"pending", "running"}:
            raise HTTPException(409, "Conversation is still generating.")
        if not has_paid_access(db, current_user) and cv_session.message_count >= MAX_MESSAGES_PER_SESSION:
            raise HTTPException(429, f"Conversation limit of {MAX_MESSAGES_PER_SESSION} messages reached.")

        assistant_msgs = db.scalars(
            select(Message)
            .where(Message.cv_session_id == cv_session.id, Message.role == "assistant")
            .order_by(Message.created_at.desc())
        ).all()

        # A still-"pending-" conversation means no writer run has happened yet — valid
        # only when the requirements gate already asked questions and this turn answers
        # them, in which case we rebuild the full first-turn context and write fresh.
        post_gate = cv_session.conversation_id.startswith("pending-")
        if post_gate and not any(m.content.get("type") == "question" for m in assistant_msgs):
            raise HTTPException(409, "Conversation is not ready for follow-up messages.")

        cv_session.message_count += 1
        cv_session.status = "pending"
        cv_session.error = None

        if post_gate:
            prompt_input = _full_context_prompt(
                db, current_user.id,
                source_text=cv_session.source_cv_text,
                job_description=cv_session.job_description,
                message=user_message,
                message_label="USER MESSAGE (answers to the clarifying questions / new evidence)",
            )
            openai_conversation_id = None
            text = cv_session.source_cv_text
            if not text and cv_session.source_cv_pdf_base64:
                file_path = _pdf_to_tempfile(cv_session.source_cv_pdf_base64)
        else:
            # `kind` stays as the per-turn value from the form, so a CV session can
            # produce a cover letter (and vice versa) on a follow-up turn. Inject the
            # latest structured document so the agent edits it in place.
            openai_conversation_id = cv_session.conversation_id
            latest_structured: dict | None = next(
                (
                    m.content["structured_data"]
                    for m in assistant_msgs
                    if m.content.get("type") in ("cv", "cover_letter")
                    and m.content.get("structured_data")
                ),
                None,
            )
            if latest_structured:
                prompt_input = (
                    f"=== CURRENT DOCUMENT ===\n"
                    f"The user is iterating on THIS exact document. Edit it in place: apply "
                    f"only what the request below asks and keep everything else identical.\n"
                    f"{json.dumps(latest_structured, indent=2)}\n\n"
                    f"=== USER REQUEST ===\n{user_message}"
                )
            else:
                prompt_input = user_message
            text = None

        user_message_text = user_message
        job_description = cv_session.job_description
        page_count = cv_session.page_count

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
        page_count=page_count,
        kind=kind,
    )

    logger.info("generate_cv queued session=%s", cv_session.id)
    return StartGenerateResponse(
        session_id=str(cv_session.id),
        status=cv_session.status,
    )
