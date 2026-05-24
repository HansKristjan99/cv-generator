"""CV-generation schemas: structured CV, clarifying questions, polished LaTeX, plain replies."""

from typing import Union

from pydantic import BaseModel, Field


class JobExperience(BaseModel):
    """A single role in work history."""

    company: str = Field(..., description="Employer. Example: 'Twilio'.")
    location: str = Field(..., description="City, Country. Example: 'Tallinn, Estonia'.")
    position: str = Field(..., description="Job title. Example: 'Software Engineer (Front-End)'.")
    start_date: str = Field(..., description="Format 'MMM YYYY'. Example: 'Sep 2024'.")
    end_date: str = Field(..., description="Format 'MMM YYYY' or the literal 'Present'. Example: 'Oct 2025'.")
    bullets: list[str] = Field(
        ...,
        description=(
            "One achievement per bullet, Google X-Y-Z format: "
            "'Accomplished X, as measured by Y, by doing Z.' "
            "Lead with a strong verb, quantify impact (%, $, count, time); keep it short — "
            "one line ideal, two or three only when needed."
        ),
    )


class Education(BaseModel):
    """A single degree or program."""

    institution: str = Field(..., description="School. Example: 'University of Tartu'.")
    location: str = Field(..., description="City, Country.")
    degree: str = Field(..., description="Full degree incl. honors. Example: 'M.Sc. in Computer Science, summa cum laude'.")
    start_date: str = Field(..., description="Format 'MMM YYYY'.")
    end_date: str = Field(..., description="Format 'MMM YYYY' or 'Present'.")
    gpa: str | None = Field(..., description="GPA or grade with scale if non-obvious. Example: '3.9/4.0'.")
    thesis: str | None = Field(..., description="Thesis title or topic. Example: 'Post-quantum threshold signatures'.")
    coursework: str | None = Field(..., description="Comma-separated relevant coursework.")


class SkillSection(BaseModel):
    """One titled grouping of skills."""

    title: str = Field(..., description="Heading. Examples: 'Languages & Frameworks', 'Backend & APIs', 'Infrastructure'.")
    items: str = Field(..., description="Comma-separated items, ordered strongest to weakest.")


class Project(BaseModel):
    """A side project, OSS contribution, or notable build."""

    name: str = Field(..., description="Project name.")
    description: str = Field(..., description="One sentence: what it does and why it matters. Quantify if possible.")
    url: str | None = Field(..., description="Link to repo, demo, or paper.")


class Award(BaseModel):
    """Award, achievement, publication, scholarship, grant, competition placement, patent, or recognition."""

    title: str = Field(..., description="Award or achievement name.")
    issuer: str | None = Field(..., description="Granting body, publisher, competition, institution, or null.")
    date: str | None = Field(..., description="Format 'MMM YYYY', 'YYYY', or null.")


class CurriculumVitae(BaseModel):
    """A one-page CV. Bullets should be tight, quantified, and lead with verbs.
    Order each list most-relevant-first (usually reverse-chronological for experience and education)."""

    name: str = Field(..., description="Full name.")
    location: str = Field(..., description="Current city + country, plus work-permit/citizenship if relevant.")
    email: str = Field(..., description="Primary contact email.")
    phone: str | None = Field(..., description="International format.")
    links: list[str] = Field(..., description="URLs: portfolio, GitHub, LinkedIn, scholar, etc. Empty list if none.")
    summary: str = Field(..., description="2-4 sentence professional summary.")
    experience: list[JobExperience] = Field(..., description="Work history, most recent first.")
    education: list[Education] = Field(..., description="Degrees, most recent first.")
    skills: list[SkillSection] = Field(..., description="Skills grouped into titled sections.")
    projects: list[Project] = Field(..., description="Notable projects/OSS. Empty list if none.")
    awards: list[Award] = Field(..., description="Awards, publications, patents, etc. Empty list if none.")


class QuestionToImproveCv(BaseModel):
    """A single question to help improve the CV based on the job description."""

    question: str = Field(
        ...,
        description=(
            "A question aimed at uncovering more information to strengthen the CV. "
            "Only include if the CV is not covering all requirements comfortably."
        ),
    )
    corresponding_requirement: str = Field(
        ...,
        description="The job-description requirement this question targets.",
    )


class QuestionsToImproveCv(BaseModel):
    """Clarifying questions returned when source material doesn't satisfy the JD."""

    questions: list[QuestionToImproveCv] = Field(..., description="At least one question.")


class OtherMessage(BaseModel):
    """A plain-text assistant reply when no CV regeneration or clarifying questions are warranted.

    Use for conversational replies, refusals, meta questions about the tool, or any
    message that does not require producing a new CV."""

    text: str = Field(
        ...,
        description=(
            "Plain-text reply to the user. Plain English, no LaTeX, no markdown headings. "
            "Keep it short (one paragraph) unless the user explicitly asked for detail."
        ),
    )


class CVWriterResponse(BaseModel):
    """Top-level WriterAgent output: a CV or a plain-text reply.

    Whether to ask the candidate clarifying questions is decided up front by the
    requirements gate, not by the writer — so the writer only writes or chats."""

    content: Union[CurriculumVitae, OtherMessage] = Field(
        ...,
        description=(
            "Pick exactly one variant: "
            "(1) CurriculumVitae — the user wants a CV generated/updated; "
            "(2) OtherMessage — plain-text reply for conversational turns, refusals, or "
            "messages that don't require regenerating the CV."
        ),
    )
