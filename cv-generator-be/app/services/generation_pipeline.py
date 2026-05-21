"""Background-task orchestration: WriterAgent → (EditorAgent if CV) → persist.

Owns the end-to-end flow once the HTTP route has queued the job. Keeps `api/cv.py`
focused on routing/DTOs only.
"""

from __future__ import annotations

import base64
import logging
import uuid
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from app.agents import EditorAgent, SessionTitleAgent, WriterAgent
from app.config import MODEL
from app.db import SessionLocal
from app.models import CvSession, Message, User
from app.schemas import CurriculumVitae, OtherMessage, QuestionsToImproveCv
from app.services.latex import compile_latex_to_pdf, cv_to_latex
from app.services.openai_client import OpenAIClient
from app.services.templates.default import DEFAULT_LAYOUT
from app.services.user_data import format_user_data, update_user_memory

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    conversation_id: str
    asst_message: dict


def _run_writer_and_editor(
    client: OpenAIClient,
    prompt_input: str,
    file_path: Path | None,
    openai_conversation_id: str | None,
    template_slug: str,
    job_description: str | None,
    memory_provider: Callable[[], str],
) -> tuple[PipelineResult, object]:
    """Returns (result, writer_response_content) so the caller can update memory."""
    writer = WriterAgent(client)
    out = writer.run(prompt_input, file=file_path, conversation_id=openai_conversation_id)
    content = out.response.content
    conv_id = out.conversation_id

    if isinstance(content, QuestionsToImproveCv):
        result = PipelineResult(
            conversation_id=conv_id,
            asst_message={
                "role": "assistant",
                "type": "question",
                "content": "",
                "questions": [q.model_dump() for q in content.questions],
            },
        )
        return result, content

    if isinstance(content, OtherMessage):
        result = PipelineResult(
            conversation_id=conv_id,
            asst_message={"role": "assistant", "type": "text", "content": content.text},
        )
        return result, content

    assert isinstance(content, CurriculumVitae)
    initial_latex = cv_to_latex(content, template_slug, DEFAULT_LAYOUT)
    initial = compile_latex_to_pdf(initial_latex)
    if not initial.success:
        logger.error("Initial CV compilation failed: %s", initial.error)

    edit = EditorAgent(client, memory_provider=memory_provider).run(
        cv=content,
        layout=DEFAULT_LAYOUT,
        template_slug=template_slug,
        initial_compile=initial,
        target_pages=content.target_pages,
        job_description=job_description,
    )
    final_latex = edit.latex
    final_pdf = edit.pdf_bytes
    pdf_b64 = base64.b64encode(final_pdf).decode() if final_pdf else ""
    logger.info(
        "Editor done iterations=%d page_count=%d target=%d hit=%s",
        edit.iterations, edit.page_count, content.target_pages, edit.hit_target,
    )

    result = PipelineResult(
        conversation_id=conv_id,
        asst_message={
            "role": "assistant",
            "type": "cv",
            "content": final_latex,
            "pdf_base64": pdf_b64,
        },
    )
    return result, content


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
            result, writer_content = _run_writer_and_editor(
                client, prompt_input, file_path, openai_conversation_id,
                template_slug, job_description,
                memory_provider=lambda: format_user_data(db, user_id),
            )

            if cv_session.conversation_id.startswith("pending-"):
                cv_session.conversation_id = result.conversation_id

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
