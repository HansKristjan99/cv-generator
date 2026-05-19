"""CV generation (`/cv/generate/`) and clarifying-answer drafting (`/cv/invent/`)."""

import base64
import logging
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Any
from uuid import uuid4

import openai
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import (
    MAX_CV_TEXT_CHARS,
    MAX_FILE_SIZE_BYTES,
    MAX_INVENT_QUESTIONS,
    MAX_INVENTS_PER_MONTH,
    MAX_JOB_DESCRIPTION_CHARS,
    MAX_MESSAGES_PER_SESSION,
    MAX_SESSIONS_PER_MONTH,
    MAX_USER_MESSAGE_CHARS,
    MODEL,
)
from app.db import get_db
from app.models import CvSession, Template, User
from app.schemas import (
    CurriculumVitae,
    CVWriterResponse,
    InventedExperience,
    QuestionsToImproveCv,
    QuestionToImproveCv,
)
from app.services.auth import CurrentUser, ensure_current_user
from app.services.latex import compile_latex_to_pdf, cv_to_latex
from app.services.openai_client import OpenAIClient
from app.services.prompts import CV_SYSTEM_PROMPT, INVENT_SYSTEM_PROMPT
from app.services.user_data import format_user_data, update_user_memory

router = APIRouter(prefix="/cv", tags=["cv"])

logger = logging.getLogger(__name__)

_TOOL_ERROR_CAP = 600


# --------------------------------------------------------------------------
# Limit helpers
# --------------------------------------------------------------------------


def _month_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _check_session_available(user_id: Any, db: Session) -> None:
    count = db.scalar(
        select(func.count(CvSession.id)).where(
            CvSession.user_id == user_id,
            CvSession.created_at >= _month_start(),
        )
    ) or 0
    if count >= MAX_SESSIONS_PER_MONTH:
        raise HTTPException(429, f"Monthly limit of {MAX_SESSIONS_PER_MONTH} CV sessions reached.")


def _get_session_for_followup(conversation_id: str, user_id: Any, db: Session) -> CvSession:
    session = db.scalar(
        select(CvSession).where(
            CvSession.conversation_id == conversation_id,
            CvSession.user_id == user_id,
        )
    )
    if session is None:
        raise HTTPException(404, "Unknown or expired conversation.")
    if session.message_count >= MAX_MESSAGES_PER_SESSION:
        raise HTTPException(429, f"Conversation limit of {MAX_MESSAGES_PER_SESSION} messages reached.")
    return session


def _get_session_for_invent(conversation_id: str, user_id: Any, db: Session) -> CvSession:
    session = db.scalar(
        select(CvSession).where(
            CvSession.conversation_id == conversation_id,
            CvSession.user_id == user_id,
        )
    )
    if session is None:
        raise HTTPException(404, "Unknown or expired conversation.")
    return session


def _check_invent_available(user_id: Any, db: Session) -> None:
    total = db.scalar(
        select(func.sum(CvSession.invent_count)).where(
            CvSession.user_id == user_id,
            CvSession.created_at >= _month_start(),
        )
    ) or 0
    if total >= MAX_INVENTS_PER_MONTH:
        raise HTTPException(429, f"Monthly limit of {MAX_INVENTS_PER_MONTH} CV enhancements reached.")


# --------------------------------------------------------------------------
# POST /cv/generate/
# --------------------------------------------------------------------------


class CvGeneratedResponse(BaseModel):
    latex: str
    pdf_base64: str


class CvQuestionResponse(BaseModel):
    questions: list[QuestionToImproveCv]


class GenerateCVResponse(BaseModel):
    conversation_id: str
    content: CvGeneratedResponse | CvQuestionResponse


COMPILE_TOOL = {
    "type": "function",
    "name": "compile_cv_to_pdf",
    "description": (
        "Compile a candidate CurriculumVitae to PDF and return the rendered page count "
        "(plus any LaTeX error). Use to verify the CV fits the target page count before "
        "finalizing. You have a maximum of 3 calls."
    ),
    "parameters": CurriculumVitae.model_json_schema(),
}


def _make_tool_handler(template_slug: str) -> Any:
    def _handle_tool(name: str, args: dict[str, Any]) -> tuple[dict[str, Any], bytes | None]:
        logger.debug("Tool call requested: %s", name)
        if name != "compile_cv_to_pdf":
            logger.warning("Unknown tool requested by model: %s", name)
            return {"success": False, "error": f"Unknown tool: {name}"}, None
        try:
            cv = CurriculumVitae(**args)
        except Exception as e:
            logger.warning("Invalid CV payload from model tool call: %s", e)
            return {"success": False, "error": f"Invalid CV payload: {e}"}, None
        result = compile_latex_to_pdf(cv_to_latex(cv, template_slug))
        logger.info("compile_cv_to_pdf -> success=%s page_count=%s", result.success, result.page_count)
        return {
            "success": result.success,
            "page_count": result.page_count,
            "error": result.error[:_TOOL_ERROR_CAP] if result.error else None,
        }, result.pdf_bytes if result.success else None
    return _handle_tool


def _resolve_template_slug(
    template_id: str | None,
    user: User,
    db: Session,
) -> str:
    if template_id:
        tmpl = db.query(Template).filter(Template.id == template_id).first()
        if tmpl:
            return tmpl.slug
    if user.preferred_template_id:
        tmpl = db.query(Template).filter(Template.id == user.preferred_template_id).first()
        if tmpl:
            return tmpl.slug
    return "default"


@router.post("/generate/", response_model=GenerateCVResponse)
async def generate_cv(
    current_user: Annotated[User, Depends(ensure_current_user)],
    db: Annotated[Session, Depends(get_db)],
    user_message: str | None = Form(None),
    text: str | None = Form(None),
    job_description: str | None = Form(None),
    file: UploadFile | None = File(None),
    conversation_id: str | None = Form(None),
    template_id: str | None = Form(None),
) -> GenerateCVResponse:
    file_path: Path | None = None
    cv_session: CvSession | None = None

    logger.info(
        "generate_cv user=%s conversation_id=%s has_text=%s has_file=%s has_job_description=%s template_id=%s",
        current_user.id,
        conversation_id,
        bool(text),
        file is not None,
        bool(job_description),
        template_id,
    )

    if conversation_id is None:
        if not (text or file) or not job_description:
            raise HTTPException(400, "Provide CV (text or file) and a job description on first turn.")

        # Input size limits
        if text and len(text) > MAX_CV_TEXT_CHARS:
            raise HTTPException(413, f"CV text exceeds {MAX_CV_TEXT_CHARS:,} character limit.")
        if job_description and len(job_description) > MAX_JOB_DESCRIPTION_CHARS:
            raise HTTPException(413, f"Job description exceeds {MAX_JOB_DESCRIPTION_CHARS:,} character limit.")
        if user_message and len(user_message) > MAX_USER_MESSAGE_CHARS:
            raise HTTPException(413, f"Message exceeds {MAX_USER_MESSAGE_CHARS:,} character limit.")

        # Session limit — check then reserve a slot before calling OpenAI
        _check_session_available(current_user.id, db)
        cv_session = CvSession(
            user_id=current_user.id,
            conversation_id=f"pending-{uuid4()}",
            message_count=1,
        )
        db.add(cv_session)
        db.commit()

        if file is not None:
            file_bytes = await file.read()
            if len(file_bytes) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit.")
            with NamedTemporaryFile(delete=False, suffix=Path(file.filename or "").suffix) as tmp:
                tmp.write(file_bytes)
                file_path = Path(tmp.name)

        prompt_input = (
            f"=== CANDIDATE'S STORED PROFILE ===\n{format_user_data(db, current_user.id)}\n\n"
            f"=== SOURCE TEXT ===\n{text or '(none provided)'}\n\n"
            f"=== JOB DESCRIPTION ===\n{job_description}\n\n"
            f"=== USER MESSAGE ===\n{user_message or 'Help me write a CV tailored to this job.'}"
        )
    else:
        if not user_message:
            raise HTTPException(400, "user_message is required on follow-up turns.")
        if len(user_message) > MAX_USER_MESSAGE_CHARS:
            raise HTTPException(413, f"Message exceeds {MAX_USER_MESSAGE_CHARS:,} character limit.")

        cv_session = _get_session_for_followup(conversation_id, current_user.id, db)
        # Increment before the call — cost is incurred regardless of outcome
        cv_session.message_count += 1
        db.commit()
        prompt_input = user_message

    template_slug = _resolve_template_slug(template_id, current_user, db)
    logger.debug("Calling OpenAI for CV generation (model=%s, template=%s)", MODEL, template_slug)
    client = OpenAIClient(MODEL)
    response, conversation_id = client.get_structured_output(
        prompt_input,
        CVWriterResponse,
        system_prompt=CV_SYSTEM_PROMPT,
        file=file_path,
        conversation_id=conversation_id,
        tools=[COMPILE_TOOL],
        tool_handler=_make_tool_handler(template_slug),
    )

    # Stamp real conversation_id onto the pre-inserted slot (new sessions only)
    if cv_session.conversation_id.startswith("pending-"):
        cv_session.conversation_id = conversation_id
        db.commit()

    if response is None:
        logger.error("Model returned no parsed output for conversation_id=%s", conversation_id)
        raise HTTPException(502, "Model returned no parsed output.")

    try:
        update_user_memory(
            db,
            current_user,
            client,
            user_message or "",
            response.content.model_dump_json(),
            source_text=text,
            job_description=job_description,
            file=file_path,
        )
    except Exception:
        logger.exception("update_user_memory failed; continuing without memory update")

    if isinstance(response.content, QuestionsToImproveCv):
        logger.info("generate_cv returning %d clarifying question(s)", len(response.content.questions))
        return GenerateCVResponse(
            conversation_id=conversation_id,
            content=CvQuestionResponse(questions=response.content.questions),
        )

    latex = cv_to_latex(response.content, template_slug)
    final = compile_latex_to_pdf(latex)
    if not final.success:
        logger.error("Final CV compilation failed: %s", final.error)
    pdf_b64 = base64.b64encode(final.pdf_bytes).decode() if final.success and final.pdf_bytes else ""
    logger.info("generate_cv done conversation_id=%s pdf_generated=%s", conversation_id, bool(pdf_b64))
    return GenerateCVResponse(
        conversation_id=conversation_id,
        content=CvGeneratedResponse(latex=latex, pdf_base64=pdf_b64),
    )


# --------------------------------------------------------------------------
# GET /cv/quota
# --------------------------------------------------------------------------


class CvQuota(BaseModel):
    sessions_used: int
    sessions_limit: int
    messages_limit: int
    invents_used: int
    invents_limit: int


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
        "sessions_limit": MAX_SESSIONS_PER_MONTH,
        "messages_limit": MAX_MESSAGES_PER_SESSION,
        "invents_used": invents_used,
        "invents_limit": MAX_INVENTS_PER_MONTH,
    }


# --------------------------------------------------------------------------
# POST /cv/invent/
# --------------------------------------------------------------------------


class InventCvRequest(BaseModel):
    conversation_id: str
    job_description: str
    questions: list[QuestionToImproveCv]


class InventCvResponse(BaseModel):
    invented_answers: str


def _build_invent_prompt(
    user_memory: str,
    transcript: str,
    job_description: str,
    questions: list[QuestionToImproveCv],
) -> str:
    questions_block = "\n\n".join(
        f"QUESTION: {q.question}\nTARGET REQUIREMENT: {q.corresponding_requirement}"
        for q in questions
    )
    return (
        f"=== CANDIDATE'S STORED PROFILE ===\n{user_memory or '(none)'}\n\n"
        f"=== CONVERSATION SO FAR ===\n{transcript or '(none)'}\n\n"
        f"=== JOB DESCRIPTION ===\n{job_description}\n\n"
        f"=== CLARIFYING QUESTIONS TO ANSWER ===\n{questions_block}\n\n"
        "Invent one realistic, plausible answer for each clarifying question above, "
        "so that its target requirement becomes satisfied."
    )


@router.post("/invent/", response_model=InventCvResponse)
def invent_cv(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    payload: InventCvRequest,
) -> InventCvResponse:
    """Draft realistic, made-up answers to the clarifying questions from /cv/generate/."""
    logger.info(
        "invent_cv user=%s conversation_id=%s questions=%d",
        current_user.id,
        payload.conversation_id,
        len(payload.questions),
    )

    if not payload.conversation_id.strip():
        raise HTTPException(400, "conversation_id is required.")
    if not payload.questions:
        raise HTTPException(400, "questions is required.")
    if len(payload.questions) > MAX_INVENT_QUESTIONS:
        raise HTTPException(422, f"Maximum {MAX_INVENT_QUESTIONS} questions per request.")
    if len(payload.job_description) > MAX_JOB_DESCRIPTION_CHARS:
        raise HTTPException(413, f"Job description exceeds {MAX_JOB_DESCRIPTION_CHARS:,} character limit.")

    cv_session = _get_session_for_invent(payload.conversation_id, current_user.id, db)
    _check_invent_available(current_user.id, db)

    client = OpenAIClient(MODEL)

    try:
        transcript = client.get_conversation_transcript(payload.conversation_id)
    except openai.NotFoundError as exc:
        logger.warning("invent_cv could not read conversation %s: %s", payload.conversation_id, exc)
        raise HTTPException(404, "Unknown or expired conversation_id.") from exc

    user_memory = format_user_data(db, current_user.id)
    prompt = _build_invent_prompt(user_memory, transcript, payload.job_description, payload.questions)

    # Increment before the call — cost is incurred regardless of outcome
    cv_session.invent_count += 1
    db.commit()

    logger.debug("Calling OpenAI to invent answers (model=%s)", MODEL)
    invented, _ = client.get_structured_output(
        prompt,
        InventedExperience,
        system_prompt=INVENT_SYSTEM_PROMPT,
    )

    if invented is None:
        logger.error("invent_cv: model returned no invented answers")
        raise HTTPException(502, "Model returned no invented answers.")
    if not invented.answers:
        logger.warning("invent_cv: model returned zero answers")
        raise HTTPException(422, "No questions to answer.")

    invented_answers = "\n\n".join(
        f"> {answer.question}\n{answer.invented_answer}" for answer in invented.answers
    )
    logger.info("invent_cv done user=%s answers=%d", current_user.id, len(invented.answers))
    return InventCvResponse(invented_answers=invented_answers)
