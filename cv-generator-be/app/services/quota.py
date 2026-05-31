"""Free-tier cost guards: monthly CV-session and CV-enhancement (invent) limits.

Paid/unlimited users bypass every limit. The month boundary, the usage counters,
and the limit checks were duplicated across the cv, cv_invent and cv_sessions
routers; this is their single home.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import (
    MAX_INVENTS_PER_MONTH,
    MAX_SESSIONS_PER_MONTH,
)
from app.models import CvSession, User
from app.services.subscriptions import has_paid_access


def month_start() -> datetime:
    """First instant of the current (UTC) month."""
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def sessions_used(db: Session, user_id: UUID) -> int:
    return db.scalar(
        select(func.count(CvSession.id)).where(
            CvSession.user_id == user_id, CvSession.created_at >= month_start()
        )
    ) or 0


def invents_used(db: Session, user_id: UUID) -> int:
    return db.scalar(
        select(func.sum(CvSession.invent_count)).where(
            CvSession.user_id == user_id, CvSession.created_at >= month_start()
        )
    ) or 0


def ensure_session_available(db: Session, user: User) -> None:
    """Raise ``429`` when a free-tier user is out of monthly CV sessions."""
    if has_paid_access(db, user):
        return
    if sessions_used(db, user.id) >= MAX_SESSIONS_PER_MONTH:
        raise HTTPException(
            429, f"Monthly limit of {MAX_SESSIONS_PER_MONTH} CV sessions reached."
        )


def ensure_invent_available(db: Session, user: User) -> None:
    """Raise ``429`` when a free-tier user is out of monthly CV enhancements."""
    if has_paid_access(db, user):
        return
    if invents_used(db, user.id) >= MAX_INVENTS_PER_MONTH:
        raise HTTPException(
            429, f"Monthly limit of {MAX_INVENTS_PER_MONTH} CV enhancements reached."
        )
