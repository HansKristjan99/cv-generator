"""Extract durable profile facts from a conversation and persist them."""

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.schemas import MemoryExtraction, NewUserData
from app.services.openai_client import OpenAIClient
from app.services.prompts import MEMORY_SYSTEM_PROMPT

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
            f"- {_line(project.title, project.description, project.link)}"
            for project in projects
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
            f"- {_line(award.title, award.issuer, award.date, award.description, award.link)}"
            for award in awards
        ]))
    if notes:
        sections.append("\n".join(["Additional notes:"] + [
            f"- {note.content}" for note in notes
        ]))

    return "\n\n".join(sections) or "No stored user data yet."


def save_new_user_data(db: Session, user: User, data: NewUserData | None, memory_conversation_id: str | None) -> None:
    changed = False
    conversation_changed = False
    inserted_jobs = 0
    inserted_bullets = 0
    inserted_education = 0
    inserted_projects = 0
    inserted_skills = 0
    inserted_awards = 0
    inserted_notes = 0

    if memory_conversation_id and user.memory_conversation_id != memory_conversation_id:
        user.memory_conversation_id = memory_conversation_id
        changed = True
        conversation_changed = True

    if data is not None:
        logger.info(
            "Memory extraction returned rows for user=%s jobs=%d education=%d projects=%d skill_categories=%d awards=%d notes=%d",
            user.id,
            len(data.job_experiences),
            len(data.education_experiences),
            len(data.projects),
            len(data.skill_categories),
            len(data.awards),
            len(data.notes),
        )
        for item in data.job_experiences:
            if not item.company_name.strip() or not item.job_title.strip():
                continue
            job = JobExperience(
                user_id=user.id,
                company_name=item.company_name,
                job_title=item.job_title,
                start_date=item.start_date,
                end_date=item.end_date,
                location=item.location,
            )
            db.add(job)
            db.flush()
            changed = True
            inserted_jobs += 1
            for bullet in item.bullets:
                if bullet.bullet_points.strip():
                    db.add(JobExperienceBullet(
                        user_id=user.id,
                        job_experience_id=job.id,
                        bullet_points=bullet.bullet_points,
                        relevant_technologies=bullet.relevant_technologies,
                    ))
                    inserted_bullets += 1
        for item in data.education_experiences:
            if item.degree.strip() and item.institution.strip():
                db.add(EducationExperience(user_id=user.id, **item.model_dump()))
                changed = True
                inserted_education += 1
        for item in data.projects:
            if item.title.strip():
                db.add(Project(user_id=user.id, **item.model_dump()))
                changed = True
                inserted_projects += 1
        for category_data in data.skill_categories:
            if not category_data.name.strip():
                continue
            category = SkillCategory(user_id=user.id, name=category_data.name)
            db.add(category)
            db.flush()
            category_has_skill = False
            for item in category_data.skills:
                if item.name.strip():
                    db.add(Skill(
                        user_id=user.id,
                        skill_category_id=category.id,
                        **item.model_dump(),
                    ))
                    changed = True
                    category_has_skill = True
                    inserted_skills += 1
            if not category_has_skill:
                db.delete(category)
        for item in data.awards:
            if item.title.strip():
                db.add(Award(user_id=user.id, **item.model_dump()))
                changed = True
                inserted_awards += 1
        for item in data.notes:
            if item.content.strip() and len(item.content) <= 600:
                db.add(MemoryNote(user_id=user.id, content=item.content))
                changed = True
                inserted_notes += 1
    else:
        logger.info("Memory extraction returned no new user data for user=%s", user.id)

    if not changed:
        logger.info("Memory update noop for user=%s", user.id)
        return

    try:
        db.commit()
        logger.info(
            "Memory update committed for user=%s conversation_changed=%s jobs=%d bullets=%d education=%d projects=%d skills=%d awards=%d notes=%d",
            user.id,
            conversation_changed,
            inserted_jobs,
            inserted_bullets,
            inserted_education,
            inserted_projects,
            inserted_skills,
            inserted_awards,
            inserted_notes,
        )
    except Exception:
        db.rollback()
        logger.exception("Memory update DB commit failed for user=%s", user.id)
        raise


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
    prompt = (
        f"CURRENT STORED USER DATA:\n{format_user_data(db, user.id)}\n\n"
        f"LATEST USER MESSAGE:\n{user_message}\n\n"
        f"LATEST ASSISTANT RESPONSE:\n{assistant_response}\n\n"
        f"SOURCE CV TEXT, IF PROVIDED:\n{source_text or '(none)'}\n\n"
        f"JOB DESCRIPTION, IF PROVIDED:\n{job_description or '(none)'}"
    )
    parsed, conversation_id = client.get_structured_output(
        prompt,
        MemoryExtraction,
        file=file,
        system_prompt=MEMORY_SYSTEM_PROMPT,
        conversation_id=user.memory_conversation_id,
        max_tool_iterations=1,
    )
    new_data = parsed.new_user_data if parsed else None
    logger.info(
        "Memory extraction completed for user=%s parsed=%s has_new_data=%s conversation_id_changed=%s",
        user.id,
        parsed is not None,
        new_data is not None,
        bool(conversation_id and conversation_id != user.memory_conversation_id),
    )
    save_new_user_data(db, user, new_data, conversation_id)
