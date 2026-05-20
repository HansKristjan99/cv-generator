"""CV generation (`/cv/generate/`) and clarifying-answer drafting (`/cv/invent/`)."""

import base64
import logging
import uuid
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Any

import openai
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
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
from app.db import SessionLocal, get_db
from app.models import CvSession, Job, Message, Template, User
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


def _month_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _check_session_available(user: User, db: Session) -> None:
    if user.is_unlimited:
        return
    count = db.scalar(
        select(func.count(CvSession.id)).where(
            CvSession.user_id == user.id,
            CvSession.created_at >= _month_start(),
        )
    ) or 0
    if count >= MAX_SESSIONS_PER_MONTH:
        raise HTTPException(429, f"Monthly limit of {MAX_SESSIONS_PER_MONTH} CV sessions reached.")


def _get_session(conversation_id: str, user_id: Any, db: Session) -> CvSession:
    session = db.scalar(
        select(CvSession).where(
            CvSession.conversation_id == conversation_id,
            CvSession.user_id == user_id,
        )
    )
    if session is None:
        raise HTTPException(404, "Unknown or expired conversation.")
    return session


def _check_invent_available(user: User, db: Session) -> None:
    if user.is_unlimited:
        return
    total = db.scalar(
        select(func.sum(CvSession.invent_count)).where(
            CvSession.user_id == user.id,
            CvSession.created_at >= _month_start(),
        )
    ) or 0
    if total >= MAX_INVENTS_PER_MONTH:
        raise HTTPException(429, f"Monthly limit of {MAX_INVENTS_PER_MONTH} CV enhancements reached.")


class CvGeneratedResponse(BaseModel):
    latex: str
    pdf_base64: str


class CvQuestionResponse(BaseModel):
    questions: list[QuestionToImproveCv]


class GenerateCVResponse(BaseModel):
    conversation_id: str
    content: CvGeneratedResponse | CvQuestionResponse


class StartGenerateResponse(BaseModel):
    job_id: str
    session_id: str
    conversation_id: str


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


class _SessionTitle(BaseModel):
    title: str


_TITLE_SYSTEM_PROMPT = (
    "You write concise titles (3-6 words) for CV-tailoring sessions. "
    "Name the role and company if both are visible (e.g. 'Backend Engineer at Vercel'). "
    "If the company is missing, name the role and a distinguishing detail. "
    "No quotes, no trailing punctuation."
)


def _generate_session_title(
    client: OpenAIClient,
    job_description: str | None,
    user_message: str,
) -> str | None:
    if not job_description:
        return None
    prompt = (
        f"Job description:\n{job_description[:1200]}\n\n"
        f"User's first message:\n{user_message[:300] or '(none)'}"
    )
    try:
        result, _ = client.get_structured_output(
            prompt,
            _SessionTitle,
            system_prompt=_TITLE_SYSTEM_PROMPT,
        )
        if result and result.title:
            return result.title.strip().strip('"').strip("'")[:80]
        return None
    except Exception:
        logger.exception("Failed to generate session title")
        return None


def _run_cv_generation(
    job_id: uuid.UUID,
    cv_session_id: uuid.UUID,
    user_id: uuid.UUID,
    prompt_input: str,
    openai_conversation_id: str | None,
    template_slug: str,
    file_path: Path | None,
    user_message_text: str,
    job_description: str | None,
    cv_text: str | None,
) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            logger.error("Background task: job %s not found", job_id)
            return
        job.status = "running"
        db.commit()

        try:
            client = OpenAIClient(MODEL)
            response, conversation_id = client.get_structured_output(
                prompt_input,
                CVWriterResponse,
                system_prompt=CV_SYSTEM_PROMPT,
                file=file_path,
                conversation_id=openai_conversation_id,
                tools=[COMPILE_TOOL],
                tool_handler=_make_tool_handler(template_slug),
            )

            cv_session = db.get(CvSession, cv_session_id)
            if cv_session and cv_session.conversation_id.startswith("pending-"):
                cv_session.conversation_id = conversation_id
                db.commit()

            if response is None:
                raise RuntimeError("Model returned no parsed output.")

            user = db.get(User, user_id)
            try:
                update_user_memory(
                    db,
                    user,
                    client,
                    user_message_text,
                    response.content.model_dump_json(),
                    source_text=cv_text,
                    job_description=job_description,
                    file=file_path,
                )
            except Exception:
                logger.exception("update_user_memory failed; continuing")

            if isinstance(response.content, QuestionsToImproveCv):
                logger.info("generate_cv returning %d clarifying question(s)", len(response.content.questions))
                result = GenerateCVResponse(
                    conversation_id=conversation_id,
                    content=CvQuestionResponse(questions=response.content.questions),
                )
                asst_content: dict = {
                    "role": "assistant",
                    "type": "question",
                    "content": "",
                    "questions": [q.model_dump() for q in response.content.questions],
                }
            else:
                latex = cv_to_latex(response.content, template_slug)
                final = compile_latex_to_pdf(latex)
                if not final.success:
                    logger.error("Final CV compilation failed: %s", final.error)
                pdf_b64 = base64.b64encode(final.pdf_bytes).decode() if final.success and final.pdf_bytes else ""
                logger.info("generate_cv done conversation_id=%s pdf_generated=%s", conversation_id, bool(pdf_b64))
                result = GenerateCVResponse(
                    conversation_id=conversation_id,
                    content=CvGeneratedResponse(latex=latex, pdf_base64=pdf_b64),
                )
                asst_content = {
                    "role": "assistant",
                    "type": "cv",
                    "content": latex,
                    "pdf_base64": pdf_b64,
                }

            user_msg = Message(
                cv_session_id=cv_session_id,
                role="user",
                content={"role": "user", "type": "text", "content": user_message_text},
            )
            asst_msg = Message(cv_session_id=cv_session_id, role="assistant", content=asst_content)
            db.add(user_msg)
            db.add(asst_msg)

            if openai_conversation_id is None and cv_session and not cv_session.title:
                title = _generate_session_title(client, job_description, user_message_text)
                if title:
                    cv_session.title = title

            job.status = "succeeded"
            job.result = result.model_dump()
            db.commit()

        except Exception as e:
            logger.exception("CV generation failed for job %s", job_id)
            db.rollback()
            job = db.get(Job, job_id)
            if job:
                job.status = "failed"
                job.error = str(e)[:500]
                db.commit()
    except Exception:
        logger.exception("Unrecoverable error in background task for job %s", job_id)
    finally:
        db.close()
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)


@router.post("/generate/", response_model=StartGenerateResponse, status_code=202)
async def generate_cv(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(ensure_current_user)],
    db: Annotated[Session, Depends(get_db)],
    user_message: str | None = Form(None),
    text: str | None = Form(None),
    job_description: str | None = Form(None),
    file: UploadFile | None = File(None),
    conversation_id: str | None = Form(None),
    template_id: str | None = Form(None),
) -> StartGenerateResponse:
    file_path: Path | None = None

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

        if text and len(text) > MAX_CV_TEXT_CHARS:
            raise HTTPException(413, f"CV text exceeds {MAX_CV_TEXT_CHARS:,} character limit.")
        if job_description and len(job_description) > MAX_JOB_DESCRIPTION_CHARS:
            raise HTTPException(413, f"Job description exceeds {MAX_JOB_DESCRIPTION_CHARS:,} character limit.")
        if user_message and len(user_message) > MAX_USER_MESSAGE_CHARS:
            raise HTTPException(413, f"Message exceeds {MAX_USER_MESSAGE_CHARS:,} character limit.")

        _check_session_available(current_user, db)

        cv_session = CvSession(
            user_id=current_user.id,
            conversation_id=f"pending-{uuid.uuid4()}",
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
        openai_conversation_id = None
        user_message_text = user_message or "Help me write a CV tailored to this job."
    else:
        if not user_message:
            raise HTTPException(400, "user_message is required on follow-up turns.")
        if len(user_message) > MAX_USER_MESSAGE_CHARS:
            raise HTTPException(413, f"Message exceeds {MAX_USER_MESSAGE_CHARS:,} character limit.")

        cv_session = _get_session(conversation_id, current_user.id, db)
        if not current_user.is_unlimited and cv_session.message_count >= MAX_MESSAGES_PER_SESSION:
            raise HTTPException(429, f"Conversation limit of {MAX_MESSAGES_PER_SESSION} messages reached.")
        cv_session.message_count += 1
        db.commit()

        prompt_input = user_message
        openai_conversation_id = conversation_id
        user_message_text = user_message
        job_description = None
        text = None

    template_slug = _resolve_template_slug(template_id, current_user, db)

    job = Job(
        user_id=current_user.id,
        cv_session_id=cv_session.id,
        status="pending",
    )
    db.add(job)
    db.commit()

    background_tasks.add_task(
        _run_cv_generation,
        job_id=job.id,
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

    logger.info("generate_cv queued job=%s session=%s", job.id, cv_session.id)
    return StartGenerateResponse(
        job_id=str(job.id),
        session_id=str(cv_session.id),
        conversation_id=cv_session.conversation_id,
    )


class JobStatusResponse(BaseModel):
    status: str
    result: GenerateCVResponse | None = None
    error: str | None = None


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> JobStatusResponse:
    job = db.scalar(
        select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    )
    if job is None:
        raise HTTPException(404, "Job not found.")
    result = GenerateCVResponse(**job.result) if job.result else None
    return JobStatusResponse(status=job.status, result=result, error=job.error)


class SessionSummary(BaseModel):
    id: str
    conversation_id: str
    title: str | None
    message_count: int
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
            id=str(s.id),
            conversation_id=s.conversation_id,
            title=s.title,
            message_count=s.message_count,
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
    conversation_id: str
    title: str | None
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
            CvSession.id == session_id,
            CvSession.user_id == current_user.id,
        )
    )
    if cv_session is None:
        raise HTTPException(404, "Conversation not found.")

    msgs = db.scalars(
        select(Message)
        .where(Message.cv_session_id == cv_session.id)
        .order_by(Message.created_at)
    ).all()

    latest_pdf_base64: str | None = None
    for m in reversed(msgs):
        if m.role == "assistant" and m.content.get("type") == "cv":
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
        conversation_id=cv_session.conversation_id,
        title=cv_session.title,
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

    cv_session = _get_session(payload.conversation_id, current_user.id, db)
    _check_invent_available(current_user, db)

    client = OpenAIClient(MODEL)

    try:
        transcript = client.get_conversation_transcript(payload.conversation_id)
    except openai.NotFoundError as exc:
        logger.warning("invent_cv could not read conversation %s: %s", payload.conversation_id, exc)
        raise HTTPException(404, "Unknown or expired conversation_id.") from exc

    user_memory = format_user_data(db, current_user.id)
    prompt = _build_invent_prompt(user_memory, transcript, payload.job_description, payload.questions)

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
