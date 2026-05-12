from pydantic import BaseModel, Field

from app.src.schemas.output_types.common import Requirement


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
    """Honor, scholarship, competition placement, or recognition."""

    title: str = Field(..., description="Award name. Example: 'Estonian Math Olympiad, 2nd place'.")
    issuer: str | None = Field(..., description="Granting body.")
    date: str | None = Field(..., description="Format 'MMM YYYY' or 'YYYY'.")


class CurriculumVitae(BaseModel):
    """A one-page CV. Bullets should be tight, quantified, and lead with verbs.
    Order each list most-relevant-first (usually reverse-chronological for experience and education)."""

    name: str = Field(..., description="Full name. Example: 'Hans Kristjan Veri'.")
    type: str = Field(default="cv")
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
    awards: list[Award] = Field(..., description="Honors, scholarships, competition placements. Empty list if none.")

    job_requirements: list[Requirement] = Field(
        ...,
        description=(
            "One entry per distinct requirement in the job description. "
            "Empty list if no job description was provided."
        ),
    )
