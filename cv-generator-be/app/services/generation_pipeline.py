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

from app.agents import CoverLetterAgent, SessionTitleAgent, WriterAgent
from app.config import MODEL
from app.db import SessionLocal
from app.models import CvSession, Message, User
from app.schemas import CoverLetter, CurriculumVitae, OtherMessage, QuestionsToImproveCv
from app.services.latex import compile_latex_to_pdf, cover_letter_to_latex, cv_to_latex
from app.services.latex_escape import escape_cover_letter_for_latex, escape_cv_for_latex
from app.services.openai_client import OpenAIClient
from app.services.user_data import update_user_memory

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    conversation_id: str
    asst_message: dict


def _run_writer(
    client: OpenAIClient,
    prompt_input: str,
    file_path: Path | None,
    openai_conversation_id: str | None,
    template_slug: str,
    page_count: int,
) -> tuple[PipelineResult, object]:
    """Single-pass: writer returns a CV / questions / message; the CV path is escaped
    deterministically and compiled once. Returns ``(result, original_writer_content)``
    so the caller can update memory from the unescaped CV.
    """
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

    if isinstance(content, QuestionsToImproveCv):
        return PipelineResult(
            conversation_id=conv_id,
            asst_message={
                "role": "assistant",
                "type": "question",
                "content": "",
                "questions": [q.model_dump() for q in content.questions],
            },
        ), content

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
            if kind == "cover_letter":
                result = _run_cover_letter(
                    client, prompt_input, file_path, openai_conversation_id,
                )
            else:
                result, writer_content = _run_writer(
                    client, prompt_input, file_path, openai_conversation_id, template_slug,
                    page_count,
                )

            if cv_session.conversation_id.startswith("pending-"):
                cv_session.conversation_id = result.conversation_id

            # Memory extraction is CV-shaped; only the CV path feeds the stored profile.
            if kind != "cover_letter":
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
