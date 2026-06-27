"""`/cv/invent/` route — draft fabricated answers to clarifying questions."""

import logging
import uuid
from typing import Annotated

import openai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.invent import InventAgent
from app.config import MAX_INVENT_QUESTIONS, MODEL
from app.db import get_db
from app.schemas import QuestionToImproveCv
from app.services.auth import CurrentUser
from app.services.openai_client import OpenAIClient
from app.services.quota import ensure_invent_available
from app.services.sessions import get_user_session
from app.services.user_data import format_user_data

router = APIRouter(prefix="/cv", tags=["cv"])
logger = logging.getLogger(__name__)


class InventCvRequest(BaseModel):
    session_id: uuid.UUID
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
        "invent_cv user=%s session_id=%s questions=%d",
        current_user.id, payload.session_id, len(payload.questions),
    )
    if not payload.questions:
        raise HTTPException(400, "questions is required.")
    if len(payload.questions) > MAX_INVENT_QUESTIONS:
        raise HTTPException(422, f"Maximum {MAX_INVENT_QUESTIONS} questions per request.")

    cv_session = get_user_session(
        db, payload.session_id, current_user.id, not_found="Unknown or expired conversation."
    )
    if not cv_session.job_description:
        raise HTTPException(409, "This conversation does not have a stored job description.")
    ensure_invent_available(db, current_user)

    client = OpenAIClient(MODEL)
    # The requirements gate asks clarifying questions before any writer run, so the
    # session's conversation_id is still the local "pending-" placeholder — there is no
    # OpenAI conversation to fetch yet. Invent can proceed without a transcript.
    if cv_session.conversation_id.startswith("pending-"):
        transcript = ""
    else:
        try:
            transcript = client.get_conversation_transcript(cv_session.conversation_id)
        except openai.NotFoundError as exc:
            logger.warning("invent_cv could not read conversation %s: %s", cv_session.conversation_id, exc)
            raise HTTPException(404, "Unknown or expired conversation.") from exc

    user_memory = format_user_data(db, current_user.id)
    cv_session.invent_count += 1
    db.commit()

    invented = InventAgent(client).run(
        user_memory=user_memory,
        transcript=transcript,
        job_description=cv_session.job_description,
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
