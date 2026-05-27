"""Pydantic models for the job-applications API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

# Suggested statuses surfaced to the UI as a dropdown. The DB column is plain
# text, so users can also supply free-text values.
SUGGESTED_STATUSES = [
    "initial",
    "cv_submitted",
    "phone_screen",
    "interview",
    "final_interview",
    "offer",
    "hired",
    "rejected",
    "withdrawn",
]


class CvOut(BaseModel):
    id: UUID
    name: str
    template_id: UUID | None
    created_at: datetime


class ClOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class SaveCvFromSession(BaseModel):
    """Save the latest CV from a chat session under a user-given name."""

    name: str
    session_id: UUID


class SaveClFromSession(BaseModel):
    name: str
    session_id: UUID


class JobApplicationOut(BaseModel):
    id: UUID
    job_name: str
    job_description: str | None
    submitted_cv_id: UUID | None
    submitted_cl_id: UUID | None
    status: str
    notes: str | None
    job_requirements: dict | None
    created_at: datetime
    updated_at: datetime


class JobApplicationCreate(BaseModel):
    job_name: str
    job_description: str | None = None
    submitted_cv_id: UUID | None = None
    submitted_cl_id: UUID | None = None
    status: str = "initial"
    notes: str | None = None


class JobApplicationUpdate(BaseModel):
    job_name: str | None = None
    job_description: str | None = None
    submitted_cv_id: UUID | None = None
    submitted_cl_id: UUID | None = None
    status: str | None = None
    notes: str | None = None


class StartFromSession(BaseModel):
    """Create a job application from a CV chat session. Latest CV and cover
    letter in that session are snapshotted into the cvs/cls tables."""

    session_id: UUID
    job_name: str
