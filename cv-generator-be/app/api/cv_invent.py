"""`/cv/invent/` route — draft fabricated answers to clarifying questions."""

import logging
from datetime import datetime
from typing import Annotated

import openai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.invent import InventAgent
from app.config import (
    MAX_INVENT_QUESTIONS,
    MAX_INVENTS_PER_MONTH,
    MAX_JOB_DESCRIPTION_CHARS,
    MODEL,
)
from app.db import get_db
from app.models import CvSession, User
from app.schemas import QuestionToImproveCv
from app.services.auth import CurrentUser
from app.services.openai_client import OpenAIClient
from app.services.user_data import format_user_data

router = APIRouter(prefix="/cv", tags=["cv"])
logger = logging.getLogger(__name__)


def _month_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _check_invent_available(user: User, db: Session) -> None:
    if user.is_unlimited:
        return
    total = db.scalar(
        select(func.sum(CvSession.invent_count)).where(
            CvSession.user_id == user.id, CvSession.created_at >= _month_start(),
        )
    ) or 0
    if total >= MAX_INVENTS_PER_MONTH:
        raise HTTPException(429, f"Monthly limit of {MAX_INVENTS_PER_MONTH} CV enhancements reached.")


class InventCvRequest(BaseModel):
    conversation_id: str
    job_description: str
    questions: list[QuestionToImproveCv]


class InventCvResponse(BaseModel):
    invented_answers: str


@router.post("/invent/", response_model=InventCvResponse)
def invent_cv(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    payload: InventCvRequest,
) -> InventCvResponse:
    """Draft realistic, made-up answers to the clarifying questions from /cv/generate/."""
    logger.info(
        "invent_cv user=%s conversation_id=%s questions=%d",
        current_user.id, payload.conversation_id, len(payload.questions),
    )
    if not payload.conversation_id.strip():
        raise HTTPException(400, "conversation_id is required.")
    if not payload.questions:
        raise HTTPException(400, "questions is required.")
    if len(payload.questions) > MAX_INVENT_QUESTIONS:
        raise HTTPException(422, f"Maximum {MAX_INVENT_QUESTIONS} questions per request.")
    if len(payload.job_description) > MAX_JOB_DESCRIPTION_CHARS:
        raise HTTPException(413, f"Job description exceeds {MAX_JOB_DESCRIPTION_CHARS:,} character limit.")

    cv_session = db.scalar(
        select(CvSession).where(
            CvSession.conversation_id == payload.conversation_id,
            CvSession.user_id == current_user.id,
        )
    )
    if cv_session is None:
        raise HTTPException(404, "Unknown or expired conversation.")
    _check_invent_available(current_user, db)

    client = OpenAIClient(MODEL)
    try:
        transcript = client.get_conversation_transcript(payload.conversation_id)
    except openai.NotFoundError as exc:
        logger.warning("invent_cv could not read conversation %s: %s", payload.conversation_id, exc)
        raise HTTPException(404, "Unknown or expired conversation_id.") from exc

    user_memory = format_user_data(db, current_user.id)
    cv_session.invent_count += 1
    db.commit()

    invented = InventAgent(client).run(
        user_memory=user_memory,
        transcript=transcript,
        job_description=payload.job_description,
        questions=payload.questions,
    )
    if invented is None:
        raise HTTPException(502, "Model returned no invented answers.")
    if not invented.answers:
        raise HTTPException(422, "No questions to answer.")

    invented_answers = "\n\n".join(
        f"> {a.question}\n{a.invented_answer}" for a in invented.answers
    )
    logger.info("invent_cv done user=%s answers=%d", current_user.id, len(invented.answers))
    return InventCvResponse(invented_answers=invented_answers)
