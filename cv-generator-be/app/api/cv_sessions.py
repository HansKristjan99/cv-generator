"""Read-side routes for CV chat sessions: listing, history, quotas."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import (
    MAX_INVENTS_PER_MONTH,
    MAX_MESSAGES_PER_SESSION,
    MAX_SESSIONS_PER_MONTH,
)
from app.db import get_db
from app.models import CvSession, Message
from app.schemas import QuestionToImproveCv
from app.services.auth import CurrentUser

router = APIRouter(prefix="/cv", tags=["cv"])


def _month_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


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
        .limit(50)
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
    latest_pdf_base64: str | None


@router.get("/sessions/{session_id}/messages", response_model=LoadConversationResponse)
def get_session_messages(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> LoadConversationResponse:
    cv_session = db.scalar(
        select(CvSession).where(
            CvSession.id == session_id, CvSession.user_id == current_user.id,
        )
    )
    if cv_session is None:
        raise HTTPException(404, "Conversation not found.")

    msgs = db.scalars(
        select(Message).where(Message.cv_session_id == cv_session.id).order_by(Message.created_at)
    ).all()

    latest_pdf_base64: str | None = None
    for m in reversed(msgs):
        if m.role == "assistant" and m.content.get("type") in ("cv", "cover_letter"):
            latest_pdf_base64 = m.content.get("pdf_base64") or None
            break

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
        latest_pdf_base64=latest_pdf_base64,
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
    month = _month_start()
    sessions_used = db.scalar(
        select(func.count(CvSession.id)).where(
            CvSession.user_id == user.id, CvSession.created_at >= month
        )
    ) or 0
    invents_used = db.scalar(
        select(func.sum(CvSession.invent_count)).where(
            CvSession.user_id == user.id, CvSession.created_at >= month
        )
    ) or 0
    return {
        "sessions_used": sessions_used,
        "sessions_limit": None if user.is_unlimited else MAX_SESSIONS_PER_MONTH,
        "messages_limit": None if user.is_unlimited else MAX_MESSAGES_PER_SESSION,
        "invents_used": invents_used,
        "invents_limit": None if user.is_unlimited else MAX_INVENTS_PER_MONTH,
        "is_unlimited": user.is_unlimited,
    }
