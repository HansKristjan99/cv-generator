"""Read-side routes for CV chat sessions: listing, history, quotas."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import (
    MAX_INVENTS_PER_MONTH,
    MAX_MESSAGES_PER_SESSION,
    MAX_SESSIONS_PER_MONTH,
    SESSION_LIST_LIMIT,
)
from app.db import get_db
from app.models import CvSession, Message
from app.schemas import QuestionToImproveCv
from app.services.auth import CurrentUser
from app.services.quota import invents_used, sessions_used
from app.services.sessions import get_user_session, latest_document
from app.services.subscriptions import has_paid_access

router = APIRouter(prefix="/cv", tags=["cv"])


class SessionSummary(BaseModel):
    id: str
    title: str | None
    message_count: int
    page_count: int
    status: str
    error: str | None
    created_at: datetime


@router.get("/sessions/", response_model=list[SessionSummary])
def list_sessions(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[SessionSummary]:
    sessions = db.scalars(
        select(CvSession)
        .where(CvSession.user_id == current_user.id)
        .order_by(CvSession.created_at.desc())
        .limit(SESSION_LIST_LIMIT)
    ).all()
    return [
        SessionSummary(
            id=str(s.id), title=s.title, message_count=s.message_count,
            page_count=s.page_count, status=s.status, error=s.error,
            created_at=s.created_at,
        )
        for s in sessions
    ]


class ChatMessageResponse(BaseModel):
    role: str
    type: str
    content: str
    questions: list[QuestionToImproveCv] | None = None


class LoadConversationResponse(BaseModel):
    title: str | None
    status: str
    error: str | None
    page_count: int
    messages: list[ChatMessageResponse]
    job_description: str | None
    job_requirements: dict | None
    source_cv_text: str | None
    source_cv_pdf_base64: str | None
    latest_cv_pdf_base64: str | None
    latest_cover_letter_pdf_base64: str | None
    latest_cv_structured: dict | None
    latest_cover_letter_structured: dict | None


@router.get("/sessions/{session_id}/messages", response_model=LoadConversationResponse)
def get_session_messages(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> LoadConversationResponse:
    cv_session = get_user_session(db, session_id, current_user.id)

    msgs = db.scalars(
        select(Message).where(Message.cv_session_id == cv_session.id).order_by(Message.created_at)
    ).all()

    latest_cv = latest_document(db, cv_session.id, "cv")
    latest_cl = latest_document(db, cv_session.id, "cover_letter")
    latest_cv_structured, latest_cv_pdf_base64 = latest_cv or (None, None)
    latest_cover_letter_structured, latest_cover_letter_pdf_base64 = latest_cl or (None, None)

    messages = [
        ChatMessageResponse(
            role=m.content.get("role", m.role),
            type=m.content.get("type", "text"),
            content=m.content.get("content", ""),
            questions=m.content.get("questions"),
        )
        for m in msgs
    ]
    return LoadConversationResponse(
        title=cv_session.title,
        status=cv_session.status,
        error=cv_session.error,
        page_count=cv_session.page_count,
        messages=messages,
        job_description=cv_session.job_description,
        job_requirements=cv_session.job_requirements,
        source_cv_text=cv_session.source_cv_text,
        source_cv_pdf_base64=cv_session.source_cv_pdf_base64,
        latest_cv_pdf_base64=latest_cv_pdf_base64,
        latest_cover_letter_pdf_base64=latest_cover_letter_pdf_base64,
        latest_cv_structured=latest_cv_structured,
        latest_cover_letter_structured=latest_cover_letter_structured,
    )


class CvQuota(BaseModel):
    sessions_used: int
    sessions_limit: int | None
    messages_limit: int | None
    invents_used: int
    invents_limit: int | None
    is_unlimited: bool


@router.get("/quota", response_model=CvQuota)
def get_quota(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> dict:
    paid_access = has_paid_access(db, user)
    return {
        "sessions_used": sessions_used(db, user.id),
        "sessions_limit": None if paid_access else MAX_SESSIONS_PER_MONTH,
        "messages_limit": None if paid_access else MAX_MESSAGES_PER_SESSION,
        "invents_used": invents_used(db, user.id),
        "invents_limit": None if paid_access else MAX_INVENTS_PER_MONTH,
        "is_unlimited": paid_access,
    }
