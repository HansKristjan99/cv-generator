"""Schemas for durable user facts extracted from a conversation."""

from pydantic import BaseModel, Field

from app.config import MAX_MEMORY_NOTE_CHARS


class ExtractedJobExperienceBullet(BaseModel):
    bullet_points: str = Field(..., description="A single concrete achievement or responsibility.")
    relevant_technologies: str | None = Field(..., description="Comma-separated technologies, or null.")


class ExtractedJobExperience(BaseModel):
    company_name: str = Field(..., description="Employer name.")
    job_title: str = Field(..., description="Role title.")
    start_date: str | None = Field(..., description="Human date like 'Sep 2024', or null.")
    end_date: str | None = Field(..., description="Human date like 'Present', or null.")
    location: str | None = Field(..., description="City/country, or null.")
    bullets: list[ExtractedJobExperienceBullet] = Field(..., description="New bullets for this role.")


class ExtractedEducationExperience(BaseModel):
    degree: str = Field(..., description="Degree or certificate.")
    field_of_study: str | None = Field(..., description="Major/field, or null.")
    institution: str = Field(..., description="School or institution.")
    start_date: str | None = Field(..., description="Human date, or null.")
    end_date: str | None = Field(..., description="Human date, or null.")
    description: str | None = Field(..., description="Relevant thesis, coursework, honors, or null.")


class ExtractedProject(BaseModel):
    title: str = Field(..., description="Project name.")
    description: str | None = Field(..., description="What was built and why it matters, or null.")
    link: str | None = Field(..., description="URL, or null.")


class ExtractedAward(BaseModel):
    title: str = Field(..., description="Award, achievement, publication, scholarship, grant, olympiad result, patent, or recognition.")
    issuer: str | None = Field(..., description="Granting body, publisher, competition, institution, or null.")
    date: str | None = Field(..., description="Human date like '2024' or 'May 2024', or null.")
    description: str | None = Field(..., description="Short context or result, or null.")
    link: str | None = Field(..., description="URL, DOI, publication link, or null.")


class ExtractedMemoryNote(BaseModel):
    content: str = Field(
        ...,
        max_length=MAX_MEMORY_NOTE_CHARS,
        description=(
            "A concise durable CV-relevant fact that does not fit any structured category. "
            "Use sparingly; prefer jobs, education, projects, skills, or awards whenever possible."
        ),
    )


class NewUserData(BaseModel):
    job_experiences: list[ExtractedJobExperience] = Field(..., description="New jobs not already stored.")
    education_experiences: list[ExtractedEducationExperience] = Field(..., description="New education not already stored.")
    projects: list[ExtractedProject] = Field(..., description="New projects not already stored.")
    skills: list[str] = Field(
        ...,
        description=(
            "New individual skill keywords not already stored (case-insensitive). "
            "Flat list, no categories or proficiency — e.g. ['React', 'PostgreSQL', 'Kubernetes']."
        ),
    )
    awards: list[ExtractedAward] = Field(..., description="New awards not already stored.")
    notes: list[ExtractedMemoryNote] = Field(
        default_factory=list,
        description=(
            f"Rare freeform notes under {MAX_MEMORY_NOTE_CHARS} chars. Empty list "
            "unless the fact cannot be represented elsewhere."
        ),
    )


class MemoryExtraction(BaseModel):
    new_user_data: NewUserData | None = Field(..., description="New durable user data, or null.")
