"""Job-applications router tests. Uses SQLite in-memory like test_billing.py."""

import uuid
from collections.abc import Generator
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import job_applications
from app.db import Base
from app.models import Cl, Cv, CvSession, JobApplication, Message, User
from app.schemas.job_applications import (
    JobApplicationCreate,
    JobApplicationUpdate,
    SaveCvFromSession,
    StartFromSession,
)


@pytest.fixture
def db_user() -> Generator[tuple[Session, User], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as db:
        user = User(idp_sub="clerk-user", email="user@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        yield db, user


def _make_session(db: Session, user: User, **kwargs: Any) -> CvSession:
    session = CvSession(
        user_id=user.id,
        conversation_id=str(uuid.uuid4()),
        title=kwargs.get("title", "Test session"),
        job_description=kwargs.get("job_description"),
        job_requirements=kwargs.get("job_requirements"),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _add_cv_message(db: Session, session: CvSession, structured: dict) -> None:
    db.add(
        Message(
            cv_session_id=session.id,
            role="assistant",
            content={
                "role": "assistant",
                "type": "cv",
                "content": "% latex",
                "structured_data": structured,
            },
        )
    )
    db.commit()


def test_create_and_list_application(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    out = job_applications.create_application(
        body=JobApplicationCreate(job_name="ACME — SWE"),
        current_user=user,
        db=db,
    )
    assert out.job_name == "ACME — SWE"
    assert out.status == "initial"

    listed = job_applications.list_applications(current_user=user, db=db)
    assert len(listed) == 1
    assert listed[0].id == out.id


def test_create_rejects_unowned_cv(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    other = User(idp_sub="other", email="other@example.com")
    db.add(other)
    db.commit()
    cv = Cv(user_id=other.id, name="Other CV", structured_data={"x": 1})
    db.add(cv)
    db.commit()
    db.refresh(cv)

    with pytest.raises(HTTPException) as exc:
        job_applications.create_application(
            body=JobApplicationCreate(job_name="X", submitted_cv_id=cv.id),
            current_user=user,
            db=db,
        )
    assert exc.value.status_code == 404


def test_save_cv_from_session_uses_latest_message(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    session = _make_session(db, user)
    _add_cv_message(db, session, {"name": "Older"})
    _add_cv_message(db, session, {"name": "Newest"})

    cv = job_applications.save_cv_from_session(
        body=SaveCvFromSession(name="My CV", session_id=session.id),
        current_user=user,
        db=db,
    )
    persisted = db.get(Cv, cv.id)
    assert persisted is not None
    assert persisted.name == "My CV"
    assert persisted.structured_data == {"name": "Newest"}


def test_save_cv_from_session_404_when_no_cv(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    session = _make_session(db, user)
    with pytest.raises(HTTPException) as exc:
        job_applications.save_cv_from_session(
            body=SaveCvFromSession(name="x", session_id=session.id),
            current_user=user,
            db=db,
        )
    assert exc.value.status_code == 404


def test_start_from_session_snapshots_cv_and_requirements(
    db_user: tuple[Session, User],
) -> None:
    db, user = db_user
    requirements = {"requirements": [{"requirement": "r1", "importance": "must_have", "met": True, "evidence": "e", "question": ""}]}
    session = _make_session(
        db,
        user,
        job_description="JD body",
        job_requirements=requirements,
    )
    _add_cv_message(db, session, {"name": "Hans"})

    app = job_applications.start_from_session(
        body=StartFromSession(session_id=session.id, job_name="ACME — Senior"),
        current_user=user,
        db=db,
    )

    assert app.job_name == "ACME — Senior"
    assert app.status == "cv_submitted"
    assert app.job_description == "JD body"
    assert app.job_requirements == requirements
    assert app.submitted_cv_id is not None
    assert app.submitted_cl_id is None
    cv = db.get(Cv, app.submitted_cv_id)
    assert cv is not None
    assert cv.structured_data == {"name": "Hans"}


def test_start_from_session_without_cv_uses_initial_status(
    db_user: tuple[Session, User],
) -> None:
    db, user = db_user
    session = _make_session(db, user, job_description="JD")
    app = job_applications.start_from_session(
        body=StartFromSession(session_id=session.id, job_name="Manual"),
        current_user=user,
        db=db,
    )
    assert app.status == "initial"
    assert app.submitted_cv_id is None


def test_update_application(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    app = job_applications.create_application(
        body=JobApplicationCreate(job_name="X"), current_user=user, db=db
    )
    updated = job_applications.update_application(
        application_id=app.id,
        body=JobApplicationUpdate(status="interview", notes="went well"),
        current_user=user,
        db=db,
    )
    assert updated.status == "interview"
    assert updated.notes == "went well"
    assert updated.job_name == "X"


def test_update_rejects_other_users_record(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    other = User(idp_sub="other", email="other@example.com")
    db.add(other)
    db.commit()
    other_app = JobApplication(user_id=other.id, job_name="theirs")
    db.add(other_app)
    db.commit()
    db.refresh(other_app)

    with pytest.raises(HTTPException) as exc:
        job_applications.update_application(
            application_id=other_app.id,
            body=JobApplicationUpdate(status="hired"),
            current_user=user,
            db=db,
        )
    assert exc.value.status_code == 404


def test_delete_application(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    app = job_applications.create_application(
        body=JobApplicationCreate(job_name="X"), current_user=user, db=db
    )
    job_applications.delete_application(application_id=app.id, current_user=user, db=db)
    assert job_applications.list_applications(current_user=user, db=db) == []


def test_delete_cv_unlinks_application(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    cv = Cv(user_id=user.id, name="My CV", structured_data={"name": "X"})
    db.add(cv)
    db.commit()
    db.refresh(cv)
    app_out = job_applications.create_application(
        body=JobApplicationCreate(job_name="X", submitted_cv_id=cv.id),
        current_user=user,
        db=db,
    )
    job_applications.delete_cv(cv_id=cv.id, current_user=user, db=db)

    persisted = db.get(JobApplication, app_out.id)
    assert persisted is not None
    assert persisted.submitted_cv_id is None
