"""Job applications: saved CV/CL snapshots and per-user application tracker."""

import base64
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEFAULT_TEMPLATE_SLUG
from app.db import get_db
from app.models import Cl, Cv, CvSession, JobApplication, Message, Template, User
from app.schemas import CoverLetter, CurriculumVitae
from app.schemas.job_applications import (
    ClOut,
    CvOut,
    JobApplicationCreate,
    JobApplicationOut,
    JobApplicationUpdate,
    SUGGESTED_STATUSES,
    SaveClFromSession,
    SaveCvFromSession,
    StartFromSession,
)
from app.services.auth import CurrentUser
from app.services.latex import (
    compile_latex_to_pdf,
    cover_letter_to_latex,
    cv_to_latex,
)
from app.services.latex_escape import (
    escape_cover_letter_for_latex,
    escape_cv_for_latex,
)

router = APIRouter(prefix="/job-applications", tags=["job-applications"])
logger = logging.getLogger(__name__)


# ---------- helpers ----------

def _latest_structured_from_session(
    db: Session, session: CvSession, msg_type: str
) -> dict | None:
    """Scan a session's messages reverse-chrono for the most recent assistant
    CV or cover-letter (msg_type in {'cv','cover_letter'}) and return its
    structured_data, or None if absent."""
    msgs = db.scalars(
        select(Message)
        .where(Message.cv_session_id == session.id)
        .order_by(Message.created_at)
    ).all()
    for m in reversed(msgs):
        if m.role != "assistant":
            continue
        if m.content.get("type") == msg_type:
            data = m.content.get("structured_data")
            if data:
                return data
    return None


def _to_application_out(app: JobApplication) -> JobApplicationOut:
    return JobApplicationOut(
        id=app.id,
        job_name=app.job_name,
        job_description=app.job_description,
        submitted_cv_id=app.submitted_cv_id,
        submitted_cl_id=app.submitted_cl_id,
        status=app.status,
        notes=app.notes,
        job_requirements=app.job_requirements,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


# ---------- statuses ----------

@router.get("/statuses", response_model=list[str])
def list_statuses() -> list[str]:
    return SUGGESTED_STATUSES


# ---------- saved CVs ----------

@router.get("/cvs", response_model=list[CvOut])
def list_cvs(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[Cv]:
    return db.scalars(
        select(Cv).where(Cv.user_id == current_user.id).order_by(Cv.created_at.desc())
    ).all()


@router.post("/cvs/from-session", response_model=CvOut)
def save_cv_from_session(
    body: SaveCvFromSession,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Cv:
    session = db.scalar(
        select(CvSession).where(
            CvSession.id == body.session_id, CvSession.user_id == current_user.id
        )
    )
    if session is None:
        raise HTTPException(404, "Conversation not found.")
    structured = _latest_structured_from_session(db, session, "cv")
    if structured is None:
        raise HTTPException(404, "No CV has been generated in this conversation yet.")
    cv = Cv(
        user_id=current_user.id,
        name=body.name.strip() or "Untitled CV",
        structured_data=structured,
        template_id=current_user.preferred_template_id,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


@router.delete("/cvs/{cv_id}", status_code=204)
def delete_cv(
    cv_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    cv = db.scalar(select(Cv).where(Cv.id == cv_id, Cv.user_id == current_user.id))
    if cv is None:
        raise HTTPException(404, "CV not found.")
    db.delete(cv)
    db.commit()


@router.get("/cvs/{cv_id}/pdf")
def render_cv_pdf(
    cv_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    cv = db.scalar(select(Cv).where(Cv.id == cv_id, Cv.user_id == current_user.id))
    if cv is None:
        raise HTTPException(404, "CV not found.")
    try:
        structured = CurriculumVitae.model_validate(cv.structured_data)
    except ValidationError as exc:
        raise HTTPException(422, f"Stored CV is malformed: {exc}") from exc
    slug = DEFAULT_TEMPLATE_SLUG
    if cv.template_id:
        tmpl = db.get(Template, cv.template_id)
        if tmpl:
            slug = tmpl.slug
    latex = cv_to_latex(escape_cv_for_latex(structured), slug)
    compiled = compile_latex_to_pdf(latex)
    if not compiled.success or not compiled.pdf_bytes:
        logger.error("CV %s PDF compile failed: %s", cv_id, compiled.error)
        raise HTTPException(500, "PDF compilation failed.")
    return {"pdf_base64": base64.b64encode(compiled.pdf_bytes).decode()}


# ---------- saved cover letters ----------

@router.get("/cls", response_model=list[ClOut])
def list_cls(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[Cl]:
    return db.scalars(
        select(Cl).where(Cl.user_id == current_user.id).order_by(Cl.created_at.desc())
    ).all()


@router.post("/cls/from-session", response_model=ClOut)
def save_cl_from_session(
    body: SaveClFromSession,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Cl:
    session = db.scalar(
        select(CvSession).where(
            CvSession.id == body.session_id, CvSession.user_id == current_user.id
        )
    )
    if session is None:
        raise HTTPException(404, "Conversation not found.")
    structured = _latest_structured_from_session(db, session, "cover_letter")
    if structured is None:
        raise HTTPException(404, "No cover letter has been generated in this conversation yet.")
    cl = Cl(
        user_id=current_user.id,
        name=body.name.strip() or "Untitled cover letter",
        structured_data=structured,
    )
    db.add(cl)
    db.commit()
    db.refresh(cl)
    return cl


@router.delete("/cls/{cl_id}", status_code=204)
def delete_cl(
    cl_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    cl = db.scalar(select(Cl).where(Cl.id == cl_id, Cl.user_id == current_user.id))
    if cl is None:
        raise HTTPException(404, "Cover letter not found.")
    db.delete(cl)
    db.commit()


@router.get("/cls/{cl_id}/pdf")
def render_cl_pdf(
    cl_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    cl = db.scalar(select(Cl).where(Cl.id == cl_id, Cl.user_id == current_user.id))
    if cl is None:
        raise HTTPException(404, "Cover letter not found.")
    try:
        structured = CoverLetter.model_validate(cl.structured_data)
    except ValidationError as exc:
        raise HTTPException(422, f"Stored cover letter is malformed: {exc}") from exc
    latex = cover_letter_to_latex(escape_cover_letter_for_latex(structured))
    compiled = compile_latex_to_pdf(latex)
    if not compiled.success or not compiled.pdf_bytes:
        logger.error("CL %s PDF compile failed: %s", cl_id, compiled.error)
        raise HTTPException(500, "PDF compilation failed.")
    return {"pdf_base64": base64.b64encode(compiled.pdf_bytes).decode()}


# ---------- applications ----------

@router.get("", response_model=list[JobApplicationOut])
def list_applications(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[JobApplicationOut]:
    apps = db.scalars(
        select(JobApplication)
        .where(JobApplication.user_id == current_user.id)
        .order_by(JobApplication.updated_at.desc())
    ).all()
    return [_to_application_out(a) for a in apps]


@router.post("", response_model=JobApplicationOut)
def create_application(
    body: JobApplicationCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> JobApplicationOut:
    _check_owns_cv(db, current_user, body.submitted_cv_id)
    _check_owns_cl(db, current_user, body.submitted_cl_id)
    app = JobApplication(
        user_id=current_user.id,
        job_name=body.job_name.strip() or "Untitled application",
        job_description=body.job_description,
        submitted_cv_id=body.submitted_cv_id,
        submitted_cl_id=body.submitted_cl_id,
        status=body.status or "initial",
        notes=body.notes,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _to_application_out(app)


@router.post("/from-session", response_model=JobApplicationOut)
def start_from_session(
    body: StartFromSession,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> JobApplicationOut:
    session = db.scalar(
        select(CvSession).where(
            CvSession.id == body.session_id, CvSession.user_id == current_user.id
        )
    )
    if session is None:
        raise HTTPException(404, "Conversation not found.")

    name = body.job_name.strip() or session.title or "Untitled application"
    cv_structured = _latest_structured_from_session(db, session, "cv")
    cl_structured = _latest_structured_from_session(db, session, "cover_letter")

    cv_id: uuid.UUID | None = None
    cl_id: uuid.UUID | None = None
    if cv_structured is not None:
        cv = Cv(
            user_id=current_user.id,
            name=f"{name} — CV",
            structured_data=cv_structured,
            template_id=current_user.preferred_template_id,
        )
        db.add(cv)
        db.flush()
        cv_id = cv.id
    if cl_structured is not None:
        cl = Cl(
            user_id=current_user.id,
            name=f"{name} — Cover letter",
            structured_data=cl_structured,
        )
        db.add(cl)
        db.flush()
        cl_id = cl.id

    app = JobApplication(
        user_id=current_user.id,
        job_name=name,
        job_description=session.job_description,
        submitted_cv_id=cv_id,
        submitted_cl_id=cl_id,
        status="cv_submitted" if cv_id else "initial",
        job_requirements=session.job_requirements,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _to_application_out(app)


@router.patch("/{application_id}", response_model=JobApplicationOut)
def update_application(
    application_id: uuid.UUID,
    body: JobApplicationUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> JobApplicationOut:
    app = db.scalar(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    if app is None:
        raise HTTPException(404, "Application not found.")
    data = body.model_dump(exclude_unset=True)
    if "submitted_cv_id" in data:
        _check_owns_cv(db, current_user, data["submitted_cv_id"])
    if "submitted_cl_id" in data:
        _check_owns_cl(db, current_user, data["submitted_cl_id"])
    for key, value in data.items():
        setattr(app, key, value)
    db.commit()
    db.refresh(app)
    return _to_application_out(app)


@router.delete("/{application_id}", status_code=204)
def delete_application(
    application_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    app = db.scalar(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
        )
    )
    if app is None:
        raise HTTPException(404, "Application not found.")
    db.delete(app)
    db.commit()


def _check_owns_cv(db: Session, user: User, cv_id: uuid.UUID | None) -> None:
    if cv_id is None:
        return
    cv = db.scalar(select(Cv).where(Cv.id == cv_id, Cv.user_id == user.id))
    if cv is None:
        raise HTTPException(404, "CV not found.")


def _check_owns_cl(db: Session, user: User, cl_id: uuid.UUID | None) -> None:
    if cl_id is None:
        return
    cl = db.scalar(select(Cl).where(Cl.id == cl_id, Cl.user_id == user.id))
    if cl is None:
        raise HTTPException(404, "Cover letter not found.")
