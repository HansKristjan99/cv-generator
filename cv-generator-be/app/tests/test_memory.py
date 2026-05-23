import uuid
from collections.abc import Generator

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.memory import UserMemoryPatch, get_user_memory, update_user_memory
from app.db import Base
from app.models import User


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


def _patch(data: dict[str, object]) -> UserMemoryPatch:
    return UserMemoryPatch.model_validate(data)


def test_get_memory_empty(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    response = get_user_memory(current_user=user, db=db)

    assert response.model_dump(mode="json") == {
        "job_experiences": [],
        "education_experiences": [],
        "projects": [],
        "skills": [],
        "awards": [],
        "notes": [],
    }


def test_post_memory_creates_entities_with_empty_ids(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    response = update_user_memory(
        payload=_patch(
            {
                "job_experiences": [
                    {
                        "id": "",
                        "company_name": "Acme",
                        "job_title": "Engineer",
                        "location": "Zurich",
                        "bullets": [
                            {
                                "id": "",
                                "bullet_points": "Built the platform.",
                                "relevant_technologies": "Python",
                            }
                        ],
                    }
                ],
                "education_experiences": [
                    {"degree": "BSc", "institution": "University", "field_of_study": "CS"}
                ],
                "projects": [{"title": "Portfolio", "description": "Personal site"}],
                "skills": [{"name": "React"}],
                "awards": [{"title": "Olympiad finalist", "issuer": "Math Olympiad"}],
                "notes": [{"content": "Prefers remote-first roles with async collaboration."}],
            }
        ),
        current_user=user,
        db=db,
    )

    body = response.model_dump(mode="json")
    assert body["job_experiences"][0]["company_name"] == "Acme"
    assert body["job_experiences"][0]["bullets"][0]["bullet_points"] == "Built the platform."
    assert body["education_experiences"][0]["degree"] == "BSc"
    assert body["projects"][0]["title"] == "Portfolio"
    assert body["skills"][0]["name"] == "React"
    assert body["awards"][0]["title"] == "Olympiad finalist"
    assert body["notes"][0]["content"] == "Prefers remote-first roles with async collaboration."


def test_post_memory_partially_updates_without_clearing_omitted_fields(
    db_user: tuple[Session, User],
) -> None:
    db, user = db_user
    created = update_user_memory(
        payload=_patch(
            {
                "job_experiences": [
                    {
                        "company_name": "Acme",
                        "job_title": "Engineer",
                        "bullets": [{"bullet_points": "Built the platform."}],
                    }
                ]
            }
        ),
        current_user=user,
        db=db,
    ).model_dump(mode="json")
    job = created["job_experiences"][0]
    bullet = job["bullets"][0]

    response = update_user_memory(
        payload=_patch(
            {
                "job_experiences": [
                    {
                        "id": job["id"],
                        "location": "Zurich",
                        "bullets": [
                            {
                                "id": bullet["id"],
                                "relevant_technologies": "Python",
                            }
                        ],
                    }
                ]
            }
        ),
        current_user=user,
        db=db,
    )

    updated_job = response.model_dump(mode="json")["job_experiences"][0]
    assert updated_job["company_name"] == "Acme"
    assert updated_job["job_title"] == "Engineer"
    assert updated_job["location"] == "Zurich"
    assert updated_job["bullets"][0]["bullet_points"] == "Built the platform."
    assert updated_job["bullets"][0]["relevant_technologies"] == "Python"


def test_post_memory_returns_404_for_missing_owned_id(db_user: tuple[Session, User]) -> None:
    db, user = db_user

    with pytest.raises(HTTPException) as exc:
        update_user_memory(
            payload=_patch({"projects": [{"id": str(uuid.uuid4()), "title": "Missing"}]}),
            current_user=user,
            db=db,
        )

    assert exc.value.status_code == 404


def test_post_memory_returns_400_for_missing_required_create_field(
    db_user: tuple[Session, User],
) -> None:
    db, user = db_user

    with pytest.raises(HTTPException) as exc:
        update_user_memory(payload=_patch({"skills": [{}]}), current_user=user, db=db)

    assert exc.value.status_code == 400


def test_post_memory_updates_and_deletes_notes(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    created = update_user_memory(
        payload=_patch({"notes": [{"content": "Likes platform engineering."}]}),
        current_user=user,
        db=db,
    ).model_dump(mode="json")
    note = created["notes"][0]

    updated = update_user_memory(
        payload=_patch({"notes": [{"id": note["id"], "content": "Likes product engineering."}]}),
        current_user=user,
        db=db,
    ).model_dump(mode="json")

    assert updated["notes"][0]["content"] == "Likes product engineering."

    deleted = update_user_memory(
        payload=_patch({"notes": [{"id": note["id"], "delete": True}]}),
        current_user=user,
        db=db,
    ).model_dump(mode="json")

    assert deleted["notes"] == []


def test_post_memory_deletes_nested_bullet(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    created = update_user_memory(
        payload=_patch(
            {
                "job_experiences": [
                    {
                        "company_name": "Acme",
                        "job_title": "Engineer",
                        "bullets": [{"bullet_points": "Built the platform."}],
                    }
                ]
            }
        ),
        current_user=user,
        db=db,
    ).model_dump(mode="json")
    job = created["job_experiences"][0]
    bullet = job["bullets"][0]

    updated = update_user_memory(
        payload=_patch(
            {
                "job_experiences": [
                    {
                        "id": job["id"],
                        "bullets": [{"id": bullet["id"], "delete": True}],
                    }
                ]
            }
        ),
        current_user=user,
        db=db,
    ).model_dump(mode="json")

    assert updated["job_experiences"][0]["bullets"] == []


def test_post_memory_deletes_structured_entity(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    created = update_user_memory(
        payload=_patch({"projects": [{"title": "Portfolio"}]}),
        current_user=user,
        db=db,
    ).model_dump(mode="json")
    project = created["projects"][0]

    updated = update_user_memory(
        payload=_patch({"projects": [{"id": project["id"], "delete": True}]}),
        current_user=user,
        db=db,
    ).model_dump(mode="json")

    assert updated["projects"] == []


def test_post_memory_rejects_long_note(db_user: tuple[Session, User]) -> None:
    db, user = db_user

    with pytest.raises(ValueError):
        update_user_memory(
            payload=_patch({"notes": [{"content": "x" * 601}]}),
            current_user=user,
            db=db,
        )


def test_post_memory_updates_and_deletes_skills(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    created = update_user_memory(
        payload=_patch({"skills": [{"name": "React"}]}),
        current_user=user,
        db=db,
    ).model_dump(mode="json")
    skill = created["skills"][0]
    assert skill["name"] == "React"

    updated = update_user_memory(
        payload=_patch({"skills": [{"id": skill["id"], "name": "React 19"}]}),
        current_user=user,
        db=db,
    ).model_dump(mode="json")

    assert updated["skills"][0]["name"] == "React 19"

    deleted = update_user_memory(
        payload=_patch({"skills": [{"id": skill["id"], "delete": True}]}),
        current_user=user,
        db=db,
    ).model_dump(mode="json")

    assert deleted["skills"] == []


def test_post_memory_skills_deduplicate_case_insensitively(db_user: tuple[Session, User]) -> None:
    db, user = db_user
    update_user_memory(payload=_patch({"skills": [{"name": "React"}]}), current_user=user, db=db)
    result = update_user_memory(
        payload=_patch({"skills": [{"name": "react"}]}),
        current_user=user,
        db=db,
    ).model_dump(mode="json")

    assert [skill["name"] for skill in result["skills"]] == ["React"]


def test_post_memory_returns_400_for_missing_skill_name(db_user: tuple[Session, User]) -> None:
    db, user = db_user

    with pytest.raises(HTTPException) as exc:
        update_user_memory(
            payload=_patch({"skills": [{"name": "   "}]}),
            current_user=user,
            db=db,
        )

    assert exc.value.status_code == 400
