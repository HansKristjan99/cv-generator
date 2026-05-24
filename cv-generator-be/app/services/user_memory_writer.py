"""Persist newly-extracted user facts (jobs, education, projects, skills, awards, notes)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import MAX_MEMORY_NOTE_CHARS
from app.models import (
    Award,
    EducationExperience,
    JobExperience,
    JobExperienceBullet,
    MemoryNote,
    Project,
    Skill,
    User,
)
from app.schemas import NewUserData

logger = logging.getLogger(__name__)


def save_new_user_data(db: Session, user: User, data: NewUserData | None) -> None:
    changed = False
    inserted_jobs = inserted_bullets = inserted_education = 0
    inserted_projects = inserted_skills = inserted_awards = inserted_notes = 0

    if data is not None:
        logger.info(
            "Memory extraction returned rows for user=%s jobs=%d education=%d "
            "projects=%d skills=%d awards=%d notes=%d",
            user.id, len(data.job_experiences), len(data.education_experiences),
            len(data.projects), len(data.skills), len(data.awards), len(data.notes),
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
        existing_skill_names = {
            name.lower()
            for name in db.scalars(select(Skill.name).where(Skill.user_id == user.id))
        }
        for raw_skill in data.skills:
            name = raw_skill.strip()
            if name and name.lower() not in existing_skill_names:
                db.add(Skill(user_id=user.id, name=name))
                existing_skill_names.add(name.lower())
                changed = True
                inserted_skills += 1
        for item in data.awards:
            if item.title.strip():
                db.add(Award(user_id=user.id, **item.model_dump()))
                changed = True
                inserted_awards += 1
        for item in data.notes:
            if item.content.strip() and len(item.content) <= MAX_MEMORY_NOTE_CHARS:
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
            "Memory update committed for user=%s jobs=%d bullets=%d education=%d "
            "projects=%d skills=%d awards=%d notes=%d",
            user.id, inserted_jobs, inserted_bullets, inserted_education,
            inserted_projects, inserted_skills, inserted_awards, inserted_notes,
        )
    except Exception:
        db.rollback()
        logger.exception("Memory update DB commit failed for user=%s", user.id)
        raise
