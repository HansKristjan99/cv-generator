"""Background-task orchestration: WriterAgent → (EditorAgent if CV) → persist.

Owns the end-to-end flow once the HTTP route has queued the job. Keeps `api/cv.py`
focused on routing/DTOs only.
"""

from __future__ import annotations

import base64
import logging
import uuid
from pathlib import Path

from pydantic import BaseModel

from app.agents import EditorAgent, SessionTitleAgent, WriterAgent
from app.config import MODEL
from app.db import SessionLocal
from app.models import CvSession, Job, Message, User
from app.schemas import CurriculumVitae, OtherMessage, QuestionsToImproveCv
from app.services.latex import compile_latex_to_pdf, cv_to_latex
from app.services.templates.default import DEFAULT_LAYOUT
from app.services.openai_client import OpenAIClient
from app.services.user_data import update_user_memory

logger = logging.getLogger(__name__)


class CvGeneratedContent(BaseModel):
    latex: str
    pdf_base64: str


class CvQuestionContent(BaseModel):
    questions: list[dict]


class OtherTextContent(BaseModel):
    text: str


class PipelineResult(BaseModel):
    conversation_id: str
    content: CvGeneratedContent | CvQuestionContent | OtherTextContent
    asst_message: dict


def _run_writer_and_editor(
    client: OpenAIClient,
    prompt_input: str,
    file_path: Path | None,
    openai_conversation_id: str | None,
    template_slug: str,
    job_description: str | None,
) -> tuple[PipelineResult, object]:
    """Returns (result, writer_response_content) so the caller can update memory."""
    writer = WriterAgent(client)
    out = writer.run(prompt_input, file=file_path, conversation_id=openai_conversation_id)
    content = out.response.content
    conv_id = out.conversation_id

    if isinstance(content, QuestionsToImproveCv):
        result = PipelineResult(
            conversation_id=conv_id,
            content=CvQuestionContent(questions=[q.model_dump() for q in content.questions]),
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
            content=OtherTextContent(text=content.text),
            asst_message={"role": "assistant", "type": "text", "content": content.text},
        )
        return result, content

    assert isinstance(content, CurriculumVitae)
    initial_latex = cv_to_latex(content, template_slug, DEFAULT_LAYOUT)
    initial = compile_latex_to_pdf(initial_latex)
    if not initial.success:
        logger.error("Initial CV compilation failed: %s", initial.error)

    edit = EditorAgent(client).run(
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
        content=CvGeneratedContent(latex=final_latex, pdf_base64=pdf_b64),
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
        if job is None:
            logger.error("Background task: job %s not found", job_id)
            return
        job.status = "running"
        db.commit()

        try:
            client = OpenAIClient(MODEL)
            result, writer_content = _run_writer_and_editor(
                client, prompt_input, file_path, openai_conversation_id,
                template_slug, job_description,
            )

            cv_session = db.get(CvSession, cv_session_id)
            if cv_session and cv_session.conversation_id.startswith("pending-"):
                cv_session.conversation_id = result.conversation_id
                db.commit()

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
                cv_session_id=cv_session_id, role="user",
                content={"role": "user", "type": "text", "content": user_message_text},
            ))
            db.add(Message(
                cv_session_id=cv_session_id, role="assistant", content=result.asst_message,
            ))

            if openai_conversation_id is None and cv_session and not cv_session.title:
                title = SessionTitleAgent(client).run(job_description, user_message_text)
                if title:
                    cv_session.title = title

            job.status = "succeeded"
            job.result = result.model_dump()
            db.commit()

        except Exception as exc:
            logger.exception("CV generation failed for job %s", job_id)
            db.rollback()
            job = db.get(Job, job_id)
            if job:
                job.status = "failed"
                job.error = str(exc)[:500]
                db.commit()
    except Exception:
        logger.exception("Unrecoverable error in background task for job %s", job_id)
    finally:
        db.close()
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)
