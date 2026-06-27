"""Job applications: saved CV/CL snapshots and per-user application tracker."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Cl, Cv, JobApplication
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
from app.services.ownership import get_owned
from app.services.saved_documents import compile_cl_pdf, compile_cv_pdf
from app.services.sessions import get_user_session, latest_document

router = APIRouter(prefix="/job-applications", tags=["job-applications"])
logger = logging.getLogger(__name__)


# ---------- helpers ----------

def _check_owns(db: Session, model: type, item_id: uuid.UUID | None, user_id: uuid.UUID, label: str) -> None:
    """Validate that a referenced document, when supplied, belongs to the user."""
    if item_id is not None:
        get_owned(db, model, item_id, user_id, not_found=f"{label} not found.")


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
    session = get_user_session(db, body.session_id, current_user.id)
    latest = latest_document(db, session.id, "cv")
    if latest is None:
        raise HTTPException(404, "No CV has been generated in this conversation yet.")
    structured, pdf_b64 = latest
    cv = Cv(
        user_id=current_user.id,
        name=body.name.strip() or "Untitled CV",
        structured_data=structured,
        template_id=current_user.preferred_template_id,
        pdf_base64=pdf_b64,
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
    db.delete(get_owned(db, Cv, cv_id, current_user.id, not_found="CV not found."))
    db.commit()


@router.get("/cvs/{cv_id}/pdf")
def render_cv_pdf(
    cv_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    cv = get_owned(db, Cv, cv_id, current_user.id, not_found="CV not found.")
    return {"pdf_base64": cv.pdf_base64 or compile_cv_pdf(db, cv)}


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
    session = get_user_session(db, body.session_id, current_user.id)
    latest = latest_document(db, session.id, "cover_letter")
    if latest is None:
        raise HTTPException(404, "No cover letter has been generated in this conversation yet.")
    structured, pdf_b64 = latest
    cl = Cl(
        user_id=current_user.id,
        name=body.name.strip() or "Untitled cover letter",
        structured_data=structured,
        pdf_base64=pdf_b64,
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
    db.delete(get_owned(db, Cl, cl_id, current_user.id, not_found="Cover letter not found."))
    db.commit()


@router.get("/cls/{cl_id}/pdf")
def render_cl_pdf(
    cl_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    cl = get_owned(db, Cl, cl_id, current_user.id, not_found="Cover letter not found.")
    return {"pdf_base64": cl.pdf_base64 or compile_cl_pdf(db, cl)}


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
    _check_owns(db, Cv, body.submitted_cv_id, current_user.id, "CV")
    _check_owns(db, Cl, body.submitted_cl_id, current_user.id, "Cover letter")
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
    session = get_user_session(db, body.session_id, current_user.id)

    name = body.job_name.strip() or session.title or "Untitled application"
    cv_latest = latest_document(db, session.id, "cv")
    cl_latest = latest_document(db, session.id, "cover_letter")

    cv_id: uuid.UUID | None = None
    cl_id: uuid.UUID | None = None
    if cv_latest is not None:
        cv_structured, cv_pdf_b64 = cv_latest
        cv = Cv(
            user_id=current_user.id,
            name=f"{name} — CV",
            structured_data=cv_structured,
            template_id=current_user.preferred_template_id,
            pdf_base64=cv_pdf_b64,
        )
        db.add(cv)
        db.flush()
        cv_id = cv.id
    if cl_latest is not None:
        cl_structured, cl_pdf_b64 = cl_latest
        cl = Cl(
            user_id=current_user.id,
            name=f"{name} — Cover letter",
            structured_data=cl_structured,
            pdf_base64=cl_pdf_b64,
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
    app = get_owned(db, JobApplication, application_id, current_user.id, not_found="Application not found.")
    data = body.model_dump(exclude_unset=True)
    if "submitted_cv_id" in data:
        _check_owns(db, Cv, data["submitted_cv_id"], current_user.id, "CV")
    if "submitted_cl_id" in data:
        _check_owns(db, Cl, data["submitted_cl_id"], current_user.id, "Cover letter")
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
    app = get_owned(db, JobApplication, application_id, current_user.id, not_found="Application not found.")
    db.delete(app)
    db.commit()
