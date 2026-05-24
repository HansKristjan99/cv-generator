"""Pydantic models for structured LLM input/output.

Split by domain for readability. Existing call sites can still `from app.schemas import X`.

All fields are declared required (`Field(...)`) even when the type is nullable: OpenAI
structured outputs require every property in `required`, so optionality is expressed
through the nullable type, not through a default.
"""

from app.schemas.cover_letter import CoverLetter, CoverLetterWriterResponse
from app.schemas.cv import (
    Award,
    CurriculumVitae,
    CVWriterResponse,
    Education,
    JobExperience,
    OtherMessage,
    Project,
    QuestionsToImproveCv,
    QuestionToImproveCv,
    SkillSection,
)
from app.schemas.invent import InventedAnswer, InventedExperience
from app.schemas.requirements import JobRequirement, RequirementsAnalysis
from app.schemas.memory import (
    ExtractedAward,
    ExtractedEducationExperience,
    ExtractedJobExperience,
    ExtractedJobExperienceBullet,
    ExtractedMemoryNote,
    ExtractedProject,
    MemoryExtraction,
    NewUserData,
)

__all__ = [
    "Award",
    "CoverLetter",
    "CoverLetterWriterResponse",
    "CurriculumVitae",
    "CVWriterResponse",
    "Education",
    "ExtractedAward",
    "ExtractedEducationExperience",
    "ExtractedJobExperience",
    "ExtractedJobExperienceBullet",
    "ExtractedMemoryNote",
    "ExtractedProject",
    "InventedAnswer",
    "InventedExperience",
    "JobExperience",
    "JobRequirement",
    "MemoryExtraction",
    "NewUserData",
    "OtherMessage",
    "Project",
    "QuestionsToImproveCv",
    "QuestionToImproveCv",
    "RequirementsAnalysis",
    "SkillSection",
]
