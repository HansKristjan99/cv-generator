"""Background-task orchestration: WriterAgent → escape → compile → persist.

Owns the end-to-end flow once the HTTP route has queued the job. Keeps `api/cv.py`
focused on routing/DTOs only.
"""

from __future__ import annotations

import base64
import logging
import uuid
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import CoverLetterAgent, RequirementsAgent, SessionTitleAgent, WriterAgent
from app.config import MODEL
from app.db import SessionLocal
from app.models import CvSession, Message, User
from app.schemas import CoverLetter, CurriculumVitae, OtherMessage, RequirementsAnalysis
from app.schemas.requirements import format_requirements, unmet_must_haves
from app.services.latex import compile_latex_to_pdf, cover_letter_to_latex, cv_to_latex
from app.services.latex_escape import escape_cover_letter_for_latex, escape_cv_for_latex
from app.services.openai_client import OpenAIClient
from app.services.user_data import format_user_data, update_user_memory

logger = logging.getLogger(__name__)

# Cap on clarifying questions the requirements gate will ask in one turn.
_MAX_GATE_QUESTIONS = 3


class PipelineResult(BaseModel):
    conversation_id: str
    asst_message: dict


def _prior_outputs_exist(db: Session, cv_session_id: uuid.UUID) -> bool:
    """True once the session has produced a CV or a clarifying-question turn."""
    msgs = db.scalars(
        select(Message).where(
            Message.cv_session_id == cv_session_id, Message.role == "assistant"
        )
    ).all()
    return any(m.content.get("type") in ("cv", "question") for m in msgs)


def _candidate_context(db: Session, user_id: uuid.UUID, cv_text: str | None) -> str:
    return (
        f"=== SOURCE CV ===\n{cv_text or '(none provided)'}\n\n"
        f"=== STORED PROFILE ===\n{format_user_data(db, user_id)}"
    )


def _requirements_gate(
    client: OpenAIClient,
    db: Session,
    cv_session: CvSession,
    user_id: uuid.UUID,
    job_description: str | None,
    cv_text: str | None,
    file_path: Path | None,
    ask_eligible: bool,
) -> tuple[PipelineResult | None, str]:
    """Extract the job requirements once per chat (cached on the session) and decide,
    deterministically, whether to ask for missing evidence.

    Returns ``(questions_result_or_None, requirements_text)``. A non-None result means
    the gate is asking clarifying questions and the writer should be skipped this turn.
    """
    analysis: RequirementsAnalysis | None = None
    if cv_session.job_requirements:
        analysis = RequirementsAnalysis.model_validate(cv_session.job_requirements)
    elif job_description:
        analysis = RequirementsAgent(client).run(
            job_description=job_description,
            candidate_context=_candidate_context(db, user_id, cv_text),
            file=file_path,
        )
        if analysis is not None:
            cv_session.job_requirements = analysis.model_dump()
            db.commit()

    if analysis is None:
        return None, ""

    if ask_eligible:
        unmet = unmet_must_haves(analysis)[:_MAX_GATE_QUESTIONS]
        if unmet:
            questions = [
                {
                    "question": r.question.strip()
                    or f"What experience can you add for: {r.requirement}?",
                    "corresponding_requirement": r.requirement,
                }
                for r in unmet
            ]
            logger.info("Requirements gate asking %d question(s)", len(questions))
            result = PipelineResult(
                conversation_id=cv_session.conversation_id,
                asst_message={
                    "role": "assistant",
                    "type": "question",
                    "content": "",
                    "questions": questions,
                },
            )
            return result, ""  # writer is skipped this turn; requirements_text unused

    return None, format_requirements(analysis)


def _run_writer(
    client: OpenAIClient,
    prompt_input: str,
    file_path: Path | None,
    openai_conversation_id: str | None,
    template_slug: str,
    page_count: int,
    requirements_text: str = "",
) -> tuple[PipelineResult, object]:
    """Single-pass: writer returns a CV or a plain message; the CV path is escaped
    deterministically and compiled once. Returns ``(result, original_writer_content)``
    so the caller can update memory from the unescaped CV.
    """
    if requirements_text:
        prompt_input = (
            "=== JOB REQUIREMENTS (cover those the candidate can support; must-haves "
            f"first) ===\n{requirements_text}\n\n{prompt_input}"
        )
    writer = WriterAgent(client)
    out = writer.run(
        prompt_input,
        target_pages=page_count,
        template_slug=template_slug,
        file=file_path,
        conversation_id=openai_conversation_id,
    )
    content = out.response.content
    conv_id = out.conversation_id

    if isinstance(content, OtherMessage):
        return PipelineResult(
            conversation_id=conv_id,
            asst_message={"role": "assistant", "type": "text", "content": content.text},
        ), content

    assert isinstance(content, CurriculumVitae)
    escaped = escape_cv_for_latex(content)
    latex = cv_to_latex(escaped, template_slug)
    compiled = compile_latex_to_pdf(latex)
    if not compiled.success:
        logger.error("CV compilation failed: %s", compiled.error)
    pdf_b64 = base64.b64encode(compiled.pdf_bytes).decode() if compiled.pdf_bytes else ""
    logger.info(
        "WriterAgent CV compiled: success=%s page_count=%d required=%d",
        compiled.success, compiled.page_count, page_count,
    )

    return PipelineResult(
        conversation_id=conv_id,
        asst_message={
            "role": "assistant",
            "type": "cv",
            "content": latex,
            "pdf_base64": pdf_b64,
            "structured_data": content.model_dump(),
        },
    ), content


def _run_cover_letter(
    client: OpenAIClient,
    prompt_input: str,
    file_path: Path | None,
    openai_conversation_id: str | None,
) -> PipelineResult:
    """Drafts a cover letter (or a plain reply); the letter path is escaped
    deterministically and compiled once before persisting.
    """
    agent = CoverLetterAgent(client)
    out = agent.run(prompt_input, file=file_path, conversation_id=openai_conversation_id)
    content = out.response.content
    conv_id = out.conversation_id

    if isinstance(content, OtherMessage):
        return PipelineResult(
            conversation_id=conv_id,
            asst_message={"role": "assistant", "type": "text", "content": content.text},
        )

    assert isinstance(content, CoverLetter)
    latex = cover_letter_to_latex(escape_cover_letter_for_latex(content))
    compiled = compile_latex_to_pdf(latex)
    if not compiled.success:
        logger.error("Cover-letter compilation failed: %s", compiled.error)
    pdf_b64 = base64.b64encode(compiled.pdf_bytes).decode() if compiled.pdf_bytes else ""
    logger.info(
        "CoverLetterAgent compiled: success=%s page_count=%d",
        compiled.success, compiled.page_count,
    )

    return PipelineResult(
        conversation_id=conv_id,
        asst_message={
            "role": "assistant",
            "type": "cover_letter",
            "content": latex,
            "pdf_base64": pdf_b64,
            "structured_data": content.model_dump(),
        },
    )


def run_pipeline(
    *,
    cv_session_id: uuid.UUID,
    user_id: uuid.UUID,
    prompt_input: str,
    openai_conversation_id: str | None,
    template_slug: str,
    file_path: Path | None,
    user_message_text: str,
    job_description: str | None,
    cv_text: str | None,
    page_count: int,
    kind: str = "cv",
) -> None:
    db = SessionLocal()
    try:
        cv_session = db.get(CvSession, cv_session_id)
        if cv_session is None:
            logger.error("Background task: session %s not found", cv_session_id)
            return
        cv_session.status = "running"
        cv_session.error = None
        db.commit()

        try:
            client = OpenAIClient(MODEL)
            writer_content = None
            if kind == "cover_letter":
                result = _run_cover_letter(
                    client, prompt_input, file_path, openai_conversation_id,
                )
            else:
                # Requirements gate: extract once per chat, then deterministically ask
                # for missing must-have evidence or proceed to writing.
                ask_eligible = (
                    openai_conversation_id is None
                    and not _prior_outputs_exist(db, cv_session_id)
                )
                gate_result, requirements_text = _requirements_gate(
                    client, db, cv_session, user_id, job_description, cv_text, file_path,
                    ask_eligible,
                )
                if gate_result is not None:
                    result = gate_result
                else:
                    result, writer_content = _run_writer(
                        client, prompt_input, file_path, openai_conversation_id,
                        template_slug, page_count, requirements_text=requirements_text,
                    )

            if cv_session.conversation_id.startswith("pending-"):
                cv_session.conversation_id = result.conversation_id

            # Memory extraction is CV-shaped; only a produced CV feeds the stored profile
            # (skip when the gate only asked questions).
            if kind != "cover_letter" and writer_content is not None:
                user = db.get(User, user_id)
                try:
                    update_user_memory(
                        db, user, client, user_message_text,
                        writer_content.model_dump_json(),
                        source_text=cv_text,
                        job_description=job_description,
                        file=file_path,
                    )
                except Exception:
                    logger.exception("update_user_memory failed; continuing")

            db.add(Message(
                cv_session_id=cv_session_id, role="assistant", content=result.asst_message,
            ))

            if openai_conversation_id is None and not cv_session.title:
                title = SessionTitleAgent(client).run(job_description, user_message_text)
                if title:
                    cv_session.title = title

            cv_session.status = "idle"
            cv_session.error = None
            db.commit()

        except Exception as exc:
            logger.exception("CV generation failed for session %s", cv_session_id)
            db.rollback()
            cv_session = db.get(CvSession, cv_session_id)
            if cv_session:
                cv_session.status = "failed"
                cv_session.error = str(exc)[:500]
                db.commit()
    except Exception:
        logger.exception("Unrecoverable error in background task for session %s", cv_session_id)
    finally:
        db.close()
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)
