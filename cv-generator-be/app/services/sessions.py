"""Helpers for CV chat sessions and their assistant message stream.

Loading a user's session and scanning its messages for the most recent generated
document were duplicated across the cv, cv_edit, cv_invent, cv_sessions and
job_applications routers. They live here now.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CvSession, Message
from app.services.ownership import get_owned

# Assistant message ``type`` values that carry a rendered document.
DOCUMENT_TYPES = ("cv", "cover_letter")


def get_user_session(
    db: Session,
    session_id: UUID,
    user_id: UUID,
    *,
    not_found: str = "Conversation not found.",
) -> CvSession:
    """Load a chat session owned by the user, or raise ``404``."""
    return get_owned(db, CvSession, session_id, user_id, not_found=not_found)


def assistant_messages(db: Session, session_id: UUID) -> list[Message]:
    """All assistant messages for a session, oldest first."""
    return list(
        db.scalars(
            select(Message)
            .where(Message.cv_session_id == session_id, Message.role == "assistant")
            .order_by(Message.created_at)
        )
    )


def latest_document(
    db: Session, session_id: UUID, doc_type: str
) -> tuple[dict, str | None] | None:
    """Most recent assistant ``doc_type`` (``'cv'``/``'cover_letter'``) as
    ``(structured_data, pdf_base64)``; ``pdf_base64`` may be ``None``."""
    for msg in reversed(assistant_messages(db, session_id)):
        if msg.content.get("type") == doc_type:
            data = msg.content.get("structured_data")
            if data:
                return data, msg.content.get("pdf_base64") or None
    return None


def latest_structured(
    db: Session, session_id: UUID, doc_types: tuple[str, ...] = DOCUMENT_TYPES
) -> dict | None:
    """The structured data of the most recent document of any of ``doc_types``."""
    for msg in reversed(assistant_messages(db, session_id)):
        if msg.content.get("type") in doc_types and msg.content.get("structured_data"):
            return msg.content["structured_data"]
    return None
