"""Pydantic models for structured LLM input/output.

All fields are declared required (`Field(...)`) even when the type is nullable:
OpenAI structured outputs require every property in `required`, so optionality
is expressed through the nullable type, not through a default.
"""

from typing import Union

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# CV generation — the curriculum vitae the model produces.
# --------------------------------------------------------------------------


class Requirement(BaseModel):
    """One requirement extracted from the job description, paired with CV evidence."""

    requirement: str = Field(
        ...,
        description="A single requirement lifted verbatim or tightly paraphrased from the job description.",
    )
    why_satisfied_by_cv: str = Field(
        ...,
        description=(
            "Point to the exact part of the CV that satisfies this requirement "
            "(role, project, skill, education, etc.). "
            "If nothing in the CV satisfies it, write the literal string 'Not satisfied'."
        ),
    )


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
            "Lead with a strong verb, quantify impact (%, $, count, time), keep to one line. "
            "Example: 'Increased a web app's onboarding completion from 50% to 90% by rebuilding the flow into a guided single-page experience.'"
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
    """One titled grouping of skills. Section titles are arbitrary."""

    title: str = Field(..., description="Heading. Examples: 'Languages & Frameworks', 'Backend & APIs', 'Infrastructure', 'Spoken Languages', 'Other'.")
    items: str = Field(..., description="Comma-separated items, ordered strongest to weakest. Example: 'TypeScript, React, Python, Java, some Rust exposure'.")


class Project(BaseModel):
    """A side project, OSS contribution, or notable build."""

    name: str = Field(..., description="Project name.")
    description: str = Field(..., description="One sentence: what it does and why it matters. Quantify if possible.")
    url: str | None = Field(..., description="Link to repo, demo, or paper.")


class Award(BaseModel):
    """Award, achievement, publication, scholarship, grant, competition placement, patent, or recognition."""

    title: str = Field(..., description="Award or achievement name. Example: 'Estonian Math Olympiad, 2nd place'.")
    issuer: str | None = Field(..., description="Granting body, publisher, competition, institution, or null.")
    date: str | None = Field(..., description="Format 'MMM YYYY', 'YYYY', or null.")


class CurriculumVitae(BaseModel):
    """A one-page CV. Bullets should be tight, quantified, and lead with verbs.
    Order each list most-relevant-first (usually reverse-chronological for experience and education)."""

    name: str = Field(..., description="Full name. Example: 'Hans Kristjan Veri'.")
    location: str = Field(..., description="Current city + country, plus work-permit/citizenship if relevant. Example: 'Zürich, Switzerland — EU Citizen (B Permit)'.")
    email: str = Field(..., description="Primary contact email.")
    phone: str | None = Field(..., description="International format. Example: '+41 78 346 33 03'.")
    links: list[str] = Field(..., description="URLs: portfolio, GitHub, LinkedIn, scholar, etc. Empty list if none.")
    summary: str = Field(
        ...,
        description=(
            "2-4 sentence professional summary. Lead with role + specialty, "
            "back with concrete proof (stack, domain, impact), end with credentials. "
            "Example: 'Frontend-focused engineer with a background in applied cryptography and security. "
            "Track record shipping React/TypeScript apps for enterprise environments. "
            "Dual degrees in CS and Mathematics (cum laude).'"
        ),
    )
    experience: list[JobExperience] = Field(..., description="Work history, most recent first.")
    education: list[Education] = Field(..., description="Degrees, most recent first.")
    skills: list[SkillSection] = Field(..., description="Skills grouped into titled sections. Order most-relevant-to-target-role first.")
    projects: list[Project] = Field(..., description="Notable projects/OSS. Empty list if none.")
    awards: list[Award] = Field(..., description="Awards, achievements, olympiad results, scholarships, grants, publications, patents, and recognitions. Empty list if none.")
    job_requirements: list[Requirement] = Field(
        ...,
        description=(
            "One entry per distinct requirement in the job description. "
            "Empty list if no job description was provided."
        ),
    )


# --------------------------------------------------------------------------
# Clarifying questions — returned instead of a CV when evidence is missing.
# --------------------------------------------------------------------------


class QuestionToImproveCv(BaseModel):
    """A single question to help improve the CV based on the job description."""

    question: str = Field(
        ...,
        description=(
            "A question aimed at uncovering more information to strengthen the CV. "
            "Only include if the CV is not covering all requirements comfortably. "
            "Example: 'Can you tell me more about your experience with React? The job "
            "description emphasizes React, but your CV doesn't mention it.'"
        ),
    )
    corresponding_requirement: str = Field(
        ...,
        description="The job-description requirement this question targets, which the candidate has not satisfied yet.",
    )


class QuestionsToImproveCv(BaseModel):
    """Questions to help improve the CV based on the job description."""

    questions: list[QuestionToImproveCv] = Field(
        ...,
        description=(
            "Questions aimed at uncovering more information to strengthen the CV. "
            "Only include if the CV is not covering all requirements comfortably."
        ),
    )


class CVWriterResponse(BaseModel):
    """Top-level model output: either the generated CV or clarifying questions."""

    content: Union[CurriculumVitae, QuestionsToImproveCv] = Field(
        ...,
        description=(
            "The generated CV. If the CV does not satisfy all requirements well, this "
            "field instead contains a list of questions to improve the CV."
        ),
    )


# --------------------------------------------------------------------------
# Invented answers — drafted (fabricated) answers to clarifying questions.
# --------------------------------------------------------------------------


class InventedAnswer(BaseModel):
    """A fabricated but realistic answer to one clarifying question."""

    question: str = Field(..., description="The clarifying question, copied verbatim.")
    invented_answer: str = Field(
        ...,
        description=(
            "A realistic, specific, fabricated professional experience answering the question — "
            "concrete technologies, scope and plausible metrics, consistent with the candidate's "
            "stated seniority, employers, timeline and background. Written as a first-person "
            "statement, as if the candidate were answering."
        ),
    )


class InventedExperience(BaseModel):
    """Fabricated answers covering every clarifying question."""

    answers: list[InventedAnswer] = Field(..., description="One entry per clarifying question.")


# --------------------------------------------------------------------------
# Memory extraction — durable user facts pulled out of a conversation.
# --------------------------------------------------------------------------


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


class ExtractedSkill(BaseModel):
    name: str = Field(..., description="Skill name.")
    proficiency: str | None = Field(..., description="Experience level/context, or null.")


class ExtractedSkillCategory(BaseModel):
    name: str = Field(..., description="Skill category name. Examples: 'Frontend', 'Backend', 'Infrastructure', 'Languages', 'Security'.")
    skills: list[ExtractedSkill] = Field(..., description="New skills in this category.")


class ExtractedAward(BaseModel):
    title: str = Field(..., description="Award, achievement, publication, scholarship, grant, olympiad result, patent, or recognition.")
    issuer: str | None = Field(..., description="Granting body, publisher, competition, institution, or null.")
    date: str | None = Field(..., description="Human date like '2024' or 'May 2024', or null.")
    description: str | None = Field(..., description="Short context or result, or null.")
    link: str | None = Field(..., description="URL, DOI, publication link, or null.")


class ExtractedMemoryNote(BaseModel):
    content: str = Field(
        ...,
        max_length=600,
        description=(
            "A concise durable CV-relevant fact that does not fit any structured category. "
            "Use sparingly; prefer jobs, education, projects, skills, or awards whenever possible."
        ),
    )


class NewUserData(BaseModel):
    job_experiences: list[ExtractedJobExperience] = Field(..., description="New jobs not already stored.")
    education_experiences: list[ExtractedEducationExperience] = Field(..., description="New education not already stored.")
    projects: list[ExtractedProject] = Field(..., description="New projects not already stored.")
    skill_categories: list[ExtractedSkillCategory] = Field(..., description="New skill categories with new skills not already stored.")
    awards: list[ExtractedAward] = Field(..., description="New awards, publications, grants, scholarships, olympiad results, patents, or recognitions not already stored.")
    notes: list[ExtractedMemoryNote] = Field(
        default_factory=list,
        description="Rare freeform notes under 600 chars. Empty list unless the fact cannot be represented elsewhere.",
    )


class MemoryExtraction(BaseModel):
    new_user_data: NewUserData | None = Field(..., description="New durable user data, or null.")
