from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Award,
    EducationExperience,
    JobExperience,
    JobExperienceBullet,
    MemoryNote,
    Project,
    Skill,
    SkillCategory,
)
from app.services.auth import CurrentUser

router = APIRouter(prefix="/users/memory", tags=["users"])

IdIn = UUID | str | None


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobExperienceBulletOut(BaseModel):
    id: UUID
    bullet_points: str
    relevant_technologies: str | None


class JobExperienceOut(BaseModel):
    id: UUID
    company_name: str
    job_title: str
    start_date: str | None
    end_date: str | None
    location: str | None
    bullets: list[JobExperienceBulletOut]


class EducationExperienceOut(BaseModel):
    id: UUID
    degree: str
    field_of_study: str | None
    institution: str
    start_date: str | None
    end_date: str | None
    description: str | None


class ProjectOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    link: str | None


class SkillOut(BaseModel):
    id: UUID
    name: str
    proficiency: str | None


class SkillCategoryOut(BaseModel):
    id: UUID
    name: str
    skills: list[SkillOut]


class AwardOut(BaseModel):
    id: UUID
    title: str
    issuer: str | None
    date: str | None
    description: str | None
    link: str | None


class MemoryNoteOut(BaseModel):
    id: UUID
    content: str


class UserMemoryOut(BaseModel):
    job_experiences: list[JobExperienceOut]
    education_experiences: list[EducationExperienceOut]
    projects: list[ProjectOut]
    skill_categories: list[SkillCategoryOut]
    awards: list[AwardOut]
    notes: list[MemoryNoteOut]


class JobExperienceBulletPatch(StrictModel):
    id: IdIn = None
    delete: bool = False
    bullet_points: str | None = None
    relevant_technologies: str | None = None


class JobExperiencePatch(StrictModel):
    id: IdIn = None
    delete: bool = False
    company_name: str | None = None
    job_title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    bullets: list[JobExperienceBulletPatch] | None = None


class EducationExperiencePatch(StrictModel):
    id: IdIn = None
    delete: bool = False
    degree: str | None = None
    field_of_study: str | None = None
    institution: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class ProjectPatch(StrictModel):
    id: IdIn = None
    delete: bool = False
    title: str | None = None
    description: str | None = None
    link: str | None = None


class SkillPatch(StrictModel):
    id: IdIn = None
    delete: bool = False
    name: str | None = None
    proficiency: str | None = None


class SkillCategoryPatch(StrictModel):
    id: IdIn = None
    delete: bool = False
    name: str | None = None
    skills: list[SkillPatch] | None = None


class AwardPatch(StrictModel):
    id: IdIn = None
    delete: bool = False
    title: str | None = None
    issuer: str | None = None
    date: str | None = None
    description: str | None = None
    link: str | None = None


class MemoryNotePatch(StrictModel):
    id: IdIn = None
    delete: bool = False
    content: str | None = Field(default=None, max_length=600)


class UserMemoryPatch(StrictModel):
    job_experiences: list[JobExperiencePatch] | None = None
    education_experiences: list[EducationExperiencePatch] | None = None
    projects: list[ProjectPatch] | None = None
    skill_categories: list[SkillCategoryPatch] | None = None
    awards: list[AwardPatch] | None = None
    notes: list[MemoryNotePatch] | None = None


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


def _owned(db: Session, model: Any, user_id: UUID, item_id: UUID, entity: str) -> Any:
    item = db.scalar(select(model).where(model.id == item_id, model.user_id == user_id))
    if item is None:
        raise HTTPException(status_code=404, detail=f"{entity} not found")
    return item


def _delete_owned(db: Session, model: Any, user_id: UUID, item_id: UUID | None, entity: str) -> None:
    if item_id is None:
        raise HTTPException(status_code=400, detail=f"{entity} id is required for delete")
    db.delete(_owned(db, model, user_id, item_id, entity))


def _load_memory(db: Session, user_id: UUID) -> UserMemoryOut:
    jobs = list(
        db.scalars(select(JobExperience).where(JobExperience.user_id == user_id).order_by(JobExperience.id))
    )
    bullets = list(
        db.scalars(
            select(JobExperienceBullet)
            .where(JobExperienceBullet.user_id == user_id)
            .order_by(JobExperienceBullet.id)
        )
    )
    education = list(
        db.scalars(
            select(EducationExperience)
            .where(EducationExperience.user_id == user_id)
            .order_by(EducationExperience.id)
        )
    )
    projects = list(db.scalars(select(Project).where(Project.user_id == user_id).order_by(Project.id)))
    skill_categories = list(
        db.scalars(select(SkillCategory).where(SkillCategory.user_id == user_id).order_by(SkillCategory.id))
    )
    skills = list(db.scalars(select(Skill).where(Skill.user_id == user_id).order_by(Skill.id)))
    awards = list(db.scalars(select(Award).where(Award.user_id == user_id).order_by(Award.id)))
    notes = list(db.scalars(select(MemoryNote).where(MemoryNote.user_id == user_id).order_by(MemoryNote.id)))

    bullets_by_job: dict[UUID, list[JobExperienceBulletOut]] = {}
    for bullet in bullets:
        bullets_by_job.setdefault(bullet.job_experience_id, []).append(
            JobExperienceBulletOut(
                id=bullet.id,
                bullet_points=bullet.bullet_points,
                relevant_technologies=bullet.relevant_technologies,
            )
        )
    skills_by_category: dict[UUID, list[SkillOut]] = {}
    for skill in skills:
        skills_by_category.setdefault(skill.skill_category_id, []).append(
            SkillOut(id=skill.id, name=skill.name, proficiency=skill.proficiency)
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
        education_experiences=[
            EducationExperienceOut(
                id=item.id,
                degree=item.degree,
                field_of_study=item.field_of_study,
                institution=item.institution,
                start_date=item.start_date,
                end_date=item.end_date,
                description=item.description,
            )
            for item in education
        ],
        projects=[
            ProjectOut(id=item.id, title=item.title, description=item.description, link=item.link)
            for item in projects
        ],
        skill_categories=[
            SkillCategoryOut(
                id=item.id,
                name=item.name,
                skills=skills_by_category.get(item.id, []),
            )
            for item in skill_categories
        ],
        awards=[
            AwardOut(
                id=item.id,
                title=item.title,
                issuer=item.issuer,
                date=item.date,
                description=item.description,
                link=item.link,
            )
            for item in awards
        ],
        notes=[MemoryNoteOut(id=item.id, content=item.content) for item in notes],
    )


def _upsert_bullet(db: Session, user_id: UUID, job_id: UUID, payload: JobExperienceBulletPatch) -> None:
    item_id = _parse_id(payload.id, "job bullet")
    required = ("bullet_points",)
    fields = ("bullet_points", "relevant_technologies")
    if payload.delete:
        if item_id is None:
            raise HTTPException(status_code=400, detail="job bullet id is required for delete")
        item = db.scalar(
            select(JobExperienceBullet).where(
                JobExperienceBullet.id == item_id,
                JobExperienceBullet.user_id == user_id,
                JobExperienceBullet.job_experience_id == job_id,
            )
        )
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

    item = db.scalar(
        select(JobExperienceBullet).where(
            JobExperienceBullet.id == item_id,
            JobExperienceBullet.user_id == user_id,
            JobExperienceBullet.job_experience_id == job_id,
        )
    )
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
        item = _owned(db, JobExperience, user_id, item_id, "job experience")
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

    item = _owned(db, model, user_id, item_id, entity)
    _apply(payload, item, required, fields)


def _upsert_skill(db: Session, user_id: UUID, category_id: UUID, payload: SkillPatch) -> None:
    item_id = _parse_id(payload.id, "skill")
    required = ("name",)
    fields = ("name", "proficiency")
    if payload.delete:
        if item_id is None:
            raise HTTPException(status_code=400, detail="skill id is required for delete")
        item = db.scalar(
            select(Skill).where(
                Skill.id == item_id,
                Skill.user_id == user_id,
                Skill.skill_category_id == category_id,
            )
        )
        if item is None:
            raise HTTPException(status_code=404, detail="skill not found")
        db.delete(item)
        return

    if item_id is None:
        _require(payload, "skill", required)
        db.add(
            Skill(
                user_id=user_id,
                skill_category_id=category_id,
                name=payload.name or "",
                proficiency=payload.proficiency,
            )
        )
        return

    item = db.scalar(
        select(Skill).where(
            Skill.id == item_id,
            Skill.user_id == user_id,
            Skill.skill_category_id == category_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="skill not found")
    _apply(payload, item, required, fields)


def _upsert_skill_category(db: Session, user_id: UUID, payload: SkillCategoryPatch) -> None:
    item_id = _parse_id(payload.id, "skill category")
    if payload.delete:
        _delete_owned(db, SkillCategory, user_id, item_id, "skill category")
        return

    if item_id is None:
        _require(payload, "skill category", ("name",))
        item = SkillCategory(user_id=user_id, name=payload.name or "")
        db.add(item)
        db.flush()
    else:
        item = _owned(db, SkillCategory, user_id, item_id, "skill category")
        _apply(payload, item, ("name",), ("name",))

    if payload.skills is not None:
        for skill in payload.skills:
            _upsert_skill(db, user_id, item.id, skill)


def _upsert_note(db: Session, user_id: UUID, payload: MemoryNotePatch) -> None:
    item_id = _parse_id(payload.id, "note")
    if payload.delete:
        _delete_owned(db, MemoryNote, user_id, item_id, "note")
        return

    if item_id is None:
        _require(payload, "note", ("content",))
        db.add(MemoryNote(user_id=user_id, content=payload.content or ""))
        return

    item = _owned(db, MemoryNote, user_id, item_id, "note")
    _apply(payload, item, ("content",), ("content",))


@router.get("", response_model=UserMemoryOut)
def get_user_memory(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserMemoryOut:
    return _load_memory(db, current_user.id)


@router.post("", response_model=UserMemoryOut)
def update_user_memory(
    payload: UserMemoryPatch,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserMemoryOut:
    try:
        for item in payload.job_experiences or []:
            _upsert_job(db, current_user.id, item)
        for item in payload.education_experiences or []:
            _upsert_simple(
                db,
                current_user.id,
                EducationExperience,
                item,
                "education experience",
                ("degree", "institution"),
                ("degree", "field_of_study", "institution", "start_date", "end_date", "description"),
            )
        for item in payload.projects or []:
            _upsert_simple(
                db,
                current_user.id,
                Project,
                item,
                "project",
                ("title",),
                ("title", "description", "link"),
            )
        for item in payload.skill_categories or []:
            _upsert_skill_category(db, current_user.id, item)
        for item in payload.awards or []:
            _upsert_simple(
                db,
                current_user.id,
                Award,
                item,
                "award",
                ("title",),
                ("title", "issuer", "date", "description", "link"),
            )
        for item in payload.notes or []:
            _upsert_note(db, current_user.id, item)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _load_memory(db, current_user.id)
