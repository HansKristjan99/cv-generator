"""Request/response models for the user-memory editor API (`/users/memory`).

These are the CRUD DTOs the frontend memory editor speaks. They are distinct from
``schemas/memory.py``, which holds the LLM memory-*extraction* schemas.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.config import MAX_MEMORY_NOTE_CHARS

# An incoming id may arrive as a UUID, a string (possibly blank), or be absent.
IdIn = UUID | str | None


class StrictModel(BaseModel):
    """Patch payloads reject unknown fields so typos surface as 422s."""

    model_config = ConfigDict(extra="forbid")


# ---------- output ----------
# ``from_attributes`` lets these be built straight from ORM rows via
# ``model_validate(row)``, so ``load_memory`` doesn't restate every field.


class OutModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class JobExperienceBulletOut(OutModel):
    id: UUID
    bullet_points: str
    relevant_technologies: str | None


class JobExperienceOut(OutModel):
    id: UUID
    company_name: str
    job_title: str
    start_date: str | None
    end_date: str | None
    location: str | None
    bullets: list[JobExperienceBulletOut]


class EducationExperienceOut(OutModel):
    id: UUID
    degree: str
    field_of_study: str | None
    institution: str
    start_date: str | None
    end_date: str | None
    description: str | None


class ProjectOut(OutModel):
    id: UUID
    title: str
    description: str | None
    link: str | None


class SkillOut(OutModel):
    id: UUID
    name: str


class AwardOut(OutModel):
    id: UUID
    title: str
    issuer: str | None
    date: str | None
    description: str | None
    link: str | None


class MemoryNoteOut(OutModel):
    id: UUID
    content: str


class UserMemoryOut(BaseModel):
    job_experiences: list[JobExperienceOut]
    education_experiences: list[EducationExperienceOut]
    projects: list[ProjectOut]
    skills: list[SkillOut]
    awards: list[AwardOut]
    notes: list[MemoryNoteOut]


# ---------- patch (upsert/delete) ----------


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
    content: str | None = Field(default=None, max_length=MAX_MEMORY_NOTE_CHARS)


class UserMemoryPatch(StrictModel):
    job_experiences: list[JobExperiencePatch] | None = None
    education_experiences: list[EducationExperiencePatch] | None = None
    projects: list[ProjectPatch] | None = None
    skills: list[SkillPatch] | None = None
    awards: list[AwardPatch] | None = None
    notes: list[MemoryNotePatch] | None = None
