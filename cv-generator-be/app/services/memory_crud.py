"""CRUD for the user-memory editor: load the full profile and apply a patch.

A patch is a partial document: each entity may be created (no id), updated (id +
fields), or removed (id + ``delete``). All writes are scoped to the owning user.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Award,
    EducationExperience,
    JobExperience,
    JobExperienceBullet,
    MemoryNote,
    Project,
    Skill,
)
from app.schemas.user_memory import (
    AwardOut,
    EducationExperienceOut,
    IdIn,
    JobExperienceBulletOut,
    JobExperienceBulletPatch,
    JobExperienceOut,
    JobExperiencePatch,
    MemoryNoteOut,
    MemoryNotePatch,
    ProjectOut,
    SkillOut,
    SkillPatch,
    UserMemoryOut,
    UserMemoryPatch,
)
from app.services.ownership import get_owned


# ---------- field helpers ----------


def _parse_id(value: IdIn, entity: str) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    value = value.strip()
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {entity} id") from exc


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _require(payload: BaseModel, entity: str, fields: tuple[str, ...]) -> None:
    missing = [
        field
        for field in fields
        if field not in payload.model_fields_set or _is_blank(getattr(payload, field))
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required {entity} field(s): {', '.join(missing)}",
        )


def _apply(payload: BaseModel, obj: object, required: tuple[str, ...], fields: tuple[str, ...]) -> None:
    for field in fields:
        if field not in payload.model_fields_set:
            continue
        value = getattr(payload, field)
        if field in required and _is_blank(value):
            raise HTTPException(status_code=400, detail=f"{field} cannot be empty")
        setattr(obj, field, value)


def _delete_owned(db: Session, model: Any, user_id: UUID, item_id: UUID | None, entity: str) -> None:
    if item_id is None:
        raise HTTPException(status_code=400, detail=f"{entity} id is required for delete")
    db.delete(get_owned(db, model, item_id, user_id, not_found=f"{entity} not found"))


# ---------- load ----------


def load_memory(db: Session, user_id: UUID) -> UserMemoryOut:
    def rows(model: Any, order: Any) -> list[Any]:
        return list(db.scalars(select(model).where(model.user_id == user_id).order_by(order)))

    jobs = rows(JobExperience, JobExperience.id)
    bullets = rows(JobExperienceBullet, JobExperienceBullet.id)
    education = rows(EducationExperience, EducationExperience.id)
    projects = rows(Project, Project.id)
    skills = rows(Skill, func.lower(Skill.name))
    awards = rows(Award, Award.id)
    notes = rows(MemoryNote, MemoryNote.id)

    bullets_by_job: dict[UUID, list[JobExperienceBulletOut]] = {}
    for bullet in bullets:
        bullets_by_job.setdefault(bullet.job_experience_id, []).append(
            JobExperienceBulletOut.model_validate(bullet)
        )

    return UserMemoryOut(
        job_experiences=[
            JobExperienceOut(
                id=job.id,
                company_name=job.company_name,
                job_title=job.job_title,
                start_date=job.start_date,
                end_date=job.end_date,
                location=job.location,
                bullets=bullets_by_job.get(job.id, []),
            )
            for job in jobs
        ],
        education_experiences=[EducationExperienceOut.model_validate(i) for i in education],
        projects=[ProjectOut.model_validate(i) for i in projects],
        skills=[SkillOut.model_validate(i) for i in skills],
        awards=[AwardOut.model_validate(i) for i in awards],
        notes=[MemoryNoteOut.model_validate(i) for i in notes],
    )


# ---------- per-entity upserts ----------


def _upsert_bullet(db: Session, user_id: UUID, job_id: UUID, payload: JobExperienceBulletPatch) -> None:
    item_id = _parse_id(payload.id, "job bullet")
    required = ("bullet_points",)
    fields = ("bullet_points", "relevant_technologies")

    def _bullet(bid: UUID) -> JobExperienceBullet | None:
        return db.scalar(
            select(JobExperienceBullet).where(
                JobExperienceBullet.id == bid,
                JobExperienceBullet.user_id == user_id,
                JobExperienceBullet.job_experience_id == job_id,
            )
        )

    if payload.delete:
        if item_id is None:
            raise HTTPException(status_code=400, detail="job bullet id is required for delete")
        item = _bullet(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="job bullet not found")
        db.delete(item)
        return

    if item_id is None:
        _require(payload, "job bullet", required)
        db.add(
            JobExperienceBullet(
                user_id=user_id,
                job_experience_id=job_id,
                bullet_points=payload.bullet_points or "",
                relevant_technologies=payload.relevant_technologies,
            )
        )
        return

    item = _bullet(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="job bullet not found")
    _apply(payload, item, required, fields)


def _upsert_job(db: Session, user_id: UUID, payload: JobExperiencePatch) -> None:
    item_id = _parse_id(payload.id, "job experience")
    required = ("company_name", "job_title")
    fields = ("company_name", "job_title", "start_date", "end_date", "location")
    if payload.delete:
        _delete_owned(db, JobExperience, user_id, item_id, "job experience")
        return

    if item_id is None:
        _require(payload, "job experience", required)
        item = JobExperience(
            user_id=user_id,
            company_name=payload.company_name or "",
            job_title=payload.job_title or "",
            start_date=payload.start_date,
            end_date=payload.end_date,
            location=payload.location,
        )
        db.add(item)
        db.flush()
    else:
        item = get_owned(db, JobExperience, item_id, user_id, not_found="job experience not found")
        _apply(payload, item, required, fields)

    if payload.bullets is not None:
        for bullet in payload.bullets:
            _upsert_bullet(db, user_id, item.id, bullet)


def _upsert_simple(
    db: Session,
    user_id: UUID,
    model: Any,
    payload: BaseModel,
    entity: str,
    required: tuple[str, ...],
    fields: tuple[str, ...],
) -> None:
    item_id = _parse_id(getattr(payload, "id"), entity)
    if getattr(payload, "delete"):
        _delete_owned(db, model, user_id, item_id, entity)
        return

    if item_id is None:
        _require(payload, entity, required)
        db.add(model(user_id=user_id, **{field: getattr(payload, field) for field in fields}))
        return

    item = get_owned(db, model, item_id, user_id, not_found=f"{entity} not found")
    _apply(payload, item, required, fields)


def _upsert_skill(db: Session, user_id: UUID, payload: SkillPatch) -> None:
    item_id = _parse_id(payload.id, "skill")
    if payload.delete:
        _delete_owned(db, Skill, user_id, item_id, "skill")
        return

    if item_id is None:
        _require(payload, "skill", ("name",))
        name = (payload.name or "").strip()
        exists = db.scalar(
            select(Skill).where(
                Skill.user_id == user_id, func.lower(Skill.name) == name.lower()
            )
        )
        if exists is None:
            db.add(Skill(user_id=user_id, name=name))
        return

    item = get_owned(db, Skill, item_id, user_id, not_found="skill not found")
    _apply(payload, item, ("name",), ("name",))


def _upsert_note(db: Session, user_id: UUID, payload: MemoryNotePatch) -> None:
    item_id = _parse_id(payload.id, "note")
    if payload.delete:
        _delete_owned(db, MemoryNote, user_id, item_id, "note")
        return

    if item_id is None:
        _require(payload, "note", ("content",))
        db.add(MemoryNote(user_id=user_id, content=payload.content or ""))
        return

    item = get_owned(db, MemoryNote, item_id, user_id, not_found="note not found")
    _apply(payload, item, ("content",), ("content",))


# ---------- patch orchestration ----------


def apply_memory_patch(db: Session, user_id: UUID, patch: UserMemoryPatch) -> None:
    """Apply every entity change in ``patch`` in one transaction."""
    try:
        for job in patch.job_experiences or []:
            _upsert_job(db, user_id, job)
        for edu in patch.education_experiences or []:
            _upsert_simple(
                db, user_id, EducationExperience, edu, "education experience",
                ("degree", "institution"),
                ("degree", "field_of_study", "institution", "start_date", "end_date", "description"),
            )
        for project in patch.projects or []:
            _upsert_simple(
                db, user_id, Project, project, "project",
                ("title",), ("title", "description", "link"),
            )
        for skill in patch.skills or []:
            _upsert_skill(db, user_id, skill)
        for award in patch.awards or []:
            _upsert_simple(
                db, user_id, Award, award, "award",
                ("title",), ("title", "issuer", "date", "description", "link"),
            )
        for note in patch.notes or []:
            _upsert_note(db, user_id, note)
        db.commit()
    except Exception:
        db.rollback()
        raise
