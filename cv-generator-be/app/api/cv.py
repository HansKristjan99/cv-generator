"""CV generation (`/cv/generate/`) and clarifying-answer drafting (`/cv/invent/`)."""

import base64
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Any

import openai
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import MODEL
from app.db import get_db
from app.models import User
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

# Slice of a failed-compile error message handed back to the model.
_TOOL_ERROR_CAP = 600


# --------------------------------------------------------------------------
# POST /cv/generate/
# --------------------------------------------------------------------------


class CvGeneratedResponse(BaseModel):
    latex: str
    pdf_base64: str


class CvQuestionResponse(BaseModel):
    # Each question carries its target job requirement, so the client (and the
    # /cv/invent/ helper) knows which requirement each question is probing.
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


def _handle_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    logger.debug("Tool call requested: %s", name)
    if name != "compile_cv_to_pdf":
        logger.warning("Unknown tool requested by model: %s", name)
        return {"success": False, "error": f"Unknown tool: {name}"}
    try:
        cv = CurriculumVitae(**args)
    except Exception as e:
        logger.warning("Invalid CV payload from model tool call: %s", e)
        return {"success": False, "error": f"Invalid CV payload: {e}"}
    result = compile_latex_to_pdf(cv_to_latex(cv))
    logger.info("compile_cv_to_pdf -> success=%s page_count=%s", result.success, result.page_count)
    return {
        "success": result.success,
        "page_count": result.page_count,
        "error": result.error[:_TOOL_ERROR_CAP] if result.error else None,
    }


@router.post("/generate/", response_model=GenerateCVResponse)
async def generate_cv(
    current_user: Annotated[User, Depends(ensure_current_user)],
    db: Annotated[Session, Depends(get_db)],
    user_message: str | None = Form(None),
    text: str | None = Form(None),
    job_description: str | None = Form(None),
    file: UploadFile | None = File(None),
    conversation_id: str | None = Form(None),
) -> GenerateCVResponse:
    file_path: Path | None = None

    logger.info(
        "generate_cv user=%s conversation_id=%s has_text=%s has_file=%s has_job_description=%s",
        current_user.id,
        conversation_id,
        bool(text),
        file is not None,
        bool(job_description),
    )

    if conversation_id is None:
        if not (text or file) or not job_description:
            raise HTTPException(400, "Provide CV (text or file) and a job description on first turn.")
        if file is not None:
            with NamedTemporaryFile(delete=False, suffix=Path(file.filename or "").suffix) as tmp:
                tmp.write(await file.read())
                file_path = Path(tmp.name)
        prompt_input = (
            f"=== SOURCE TEXT ===\n{text or '(none provided)'}\n\n"
            f"=== JOB DESCRIPTION ===\n{job_description}\n\n"
            f"=== USER MESSAGE ===\n{user_message or 'Help me write a CV tailored to this job.'}"
        )
    else:
        if not user_message:
            raise HTTPException(400, "user_message is required on follow-up turns.")
        prompt_input = user_message

    logger.debug("Calling OpenAI for CV generation (model=%s)", MODEL)
    client = OpenAIClient(MODEL)
    response, conversation_id = client.get_structured_output(
        prompt_input,
        CVWriterResponse,
        system_prompt=CV_SYSTEM_PROMPT,
        file=file_path,
        conversation_id=conversation_id,
        tools=[COMPILE_TOOL],
        tool_handler=_handle_tool,
    )

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

    latex = cv_to_latex(response.content)
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
    """Draft realistic, made-up answers to the clarifying questions from /cv/generate/.

    This is a draft helper only: it does not generate a CV, does not append to the
    generation conversation, and intentionally does not persist anything to user
    memory — the fabricated answers are returned as text for the user to edit.
    """
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

    client = OpenAIClient(MODEL)

    try:
        transcript = client.get_conversation_transcript(payload.conversation_id)
    except openai.NotFoundError as exc:
        logger.warning("invent_cv could not read conversation %s: %s", payload.conversation_id, exc)
        raise HTTPException(404, "Unknown or expired conversation_id.") from exc

    user_memory = format_user_data(db, current_user.id)
    prompt = _build_invent_prompt(user_memory, transcript, payload.job_description, payload.questions)

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
