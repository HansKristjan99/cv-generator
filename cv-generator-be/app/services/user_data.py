"""Format the user's stored profile for prompt injection, and run the memory-extraction agent."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.memory import MemoryAgent
from app.models import (
    Award,
    EducationExperience,
    JobExperience,
    JobExperienceBullet,
    MemoryNote,
    Project,
    Skill,
    SkillCategory,
    User,
)
from app.services.openai_client import OpenAIClient
from app.services.user_memory_writer import save_new_user_data

logger = logging.getLogger(__name__)


def _line(*parts: str | None) -> str:
    return " | ".join(part for part in parts if part)


def format_user_data(db: Session, user_id: UUID) -> str:
    jobs = list(db.scalars(select(JobExperience).where(JobExperience.user_id == user_id)))
    bullets = list(db.scalars(select(JobExperienceBullet).where(JobExperienceBullet.user_id == user_id)))
    education = list(db.scalars(select(EducationExperience).where(EducationExperience.user_id == user_id)))
    projects = list(db.scalars(select(Project).where(Project.user_id == user_id)))
    skill_categories = list(db.scalars(select(SkillCategory).where(SkillCategory.user_id == user_id)))
    skills = list(db.scalars(select(Skill).where(Skill.user_id == user_id)))
    awards = list(db.scalars(select(Award).where(Award.user_id == user_id)))
    notes = list(db.scalars(select(MemoryNote).where(MemoryNote.user_id == user_id)))

    by_job: dict[UUID, list[JobExperienceBullet]] = {}
    for bullet in bullets:
        by_job.setdefault(bullet.job_experience_id, []).append(bullet)
    by_category: dict[UUID, list[Skill]] = {}
    for skill in skills:
        by_category.setdefault(skill.skill_category_id, []).append(skill)

    sections: list[str] = []
    if jobs:
        lines = ["Job experiences:"]
        for job in jobs:
            lines.append(f"- {_line(job.job_title, job.company_name, job.location, job.start_date, job.end_date)}")
            for bullet in by_job.get(job.id, []):
                lines.append(f"  - {_line(bullet.bullet_points, bullet.relevant_technologies)}")
        sections.append("\n".join(lines))
    if education:
        sections.append("\n".join(["Education:"] + [
            f"- {_line(item.degree, item.field_of_study, item.institution, item.start_date, item.end_date, item.description)}"
            for item in education
        ]))
    if projects:
        sections.append("\n".join(["Projects:"] + [
            f"- {_line(p.title, p.description, p.link)}" for p in projects
        ]))
    if skill_categories:
        lines = ["Skills:"]
        for category in skill_categories:
            lines.append(f"- {category.name}")
            for skill in by_category.get(category.id, []):
                lines.append(f"  - {_line(skill.name, skill.proficiency)}")
        sections.append("\n".join(lines))
    if awards:
        sections.append("\n".join(["Awards and Achievements:"] + [
            f"- {_line(a.title, a.issuer, a.date, a.description, a.link)}" for a in awards
        ]))
    if notes:
        sections.append("\n".join(["Additional notes:"] + [f"- {n.content}" for n in notes]))

    return "\n\n".join(sections) or "No stored user data yet."


def update_user_memory(
    db: Session,
    user: User,
    client: OpenAIClient,
    user_message: str,
    assistant_response: str,
    source_text: str | None = None,
    job_description: str | None = None,
    file: Path | None = None,
) -> None:
    logger.info("Updating user memory for user=%s", user.id)
    new_data = MemoryAgent(client).extract(
        stored_user_data=format_user_data(db, user.id),
        user_message=user_message,
        assistant_response=assistant_response,
        source_text=source_text,
        job_description=job_description,
        file=file,
    )
    logger.info("Memory extraction done user=%s has_new_data=%s", user.id, new_data is not None)
    save_new_user_data(db, user, new_data)
