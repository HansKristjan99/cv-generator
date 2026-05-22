"""Deterministic LaTeX escaping for LLM-generated plaintext.

Applied once to the CurriculumVitae object after the writer returns it. URL-position
fields (cv.email, cv.links, project.url) are intentionally skipped because they go
into ``\\href{URL}{...}`` URL positions where LaTeX-escaped underscores etc. break
the link. Templates escape those values inline when used as display text.
"""

from __future__ import annotations

from app.schemas import (
    Award,
    CurriculumVitae,
    Education,
    JobExperience,
    Project,
    SkillSection,
)

# ``str.translate`` walks the *original* string once; replacement text is never
# re-scanned, so we can safely map "\\" → "\\textbackslash{}" alongside "{" → "\\{".
_ESCAPE = str.maketrans({
    "\\": r"\textbackslash{}",
    "&":  r"\&",
    "%":  r"\%",
    "$":  r"\$",
    "#":  r"\#",
    "_":  r"\_",
    "{":  r"\{",
    "}":  r"\}",
    "~":  r"\textasciitilde{}",
    "^":  r"\textasciicircum{}",
})


def escape_tex(s: str) -> str:
    """Escape a plaintext string so it is safe to embed in a LaTeX document."""
    return s.translate(_ESCAPE)


def _opt(s: str | None) -> str | None:
    return escape_tex(s) if s is not None else None


def _job(j: JobExperience) -> JobExperience:
    return j.model_copy(update={
        "company":    escape_tex(j.company),
        "location":   escape_tex(j.location),
        "position":   escape_tex(j.position),
        "start_date": escape_tex(j.start_date),
        "end_date":   escape_tex(j.end_date),
        "bullets":    [escape_tex(b) for b in j.bullets],
    })


def _edu(e: Education) -> Education:
    return e.model_copy(update={
        "institution": escape_tex(e.institution),
        "location":    escape_tex(e.location),
        "degree":      escape_tex(e.degree),
        "start_date":  escape_tex(e.start_date),
        "end_date":    escape_tex(e.end_date),
        "gpa":         _opt(e.gpa),
        "thesis":      _opt(e.thesis),
        "coursework":  _opt(e.coursework),
    })


def _skill(s: SkillSection) -> SkillSection:
    return s.model_copy(update={
        "title": escape_tex(s.title),
        "items": escape_tex(s.items),
    })


def _project(p: Project) -> Project:
    return p.model_copy(update={
        "name":        escape_tex(p.name),
        "description": escape_tex(p.description),
        # url stays raw — it goes into \href{URL}{} and must remain a valid URL.
    })


def _award(a: Award) -> Award:
    return a.model_copy(update={
        "title":  escape_tex(a.title),
        "issuer": _opt(a.issuer),
        "date":   _opt(a.date),
    })


def escape_cv_for_latex(cv: CurriculumVitae) -> CurriculumVitae:
    """Return a deep copy of *cv* with all plaintext fields escaped for LaTeX.

    URL-position fields (``email``, ``links``, ``project.url``) are intentionally
    left raw; templates escape those for the display side of ``\\href`` themselves.
    """
    return cv.model_copy(update={
        "name":       escape_tex(cv.name),
        "location":   escape_tex(cv.location),
        "phone":      _opt(cv.phone),
        "summary":    escape_tex(cv.summary),
        # email: raw — used as mailto: URL.
        # links: raw — URLs.
        "experience": [_job(j) for j in cv.experience],
        "education":  [_edu(e) for e in cv.education],
        "skills":     [_skill(s) for s in cv.skills],
        "projects":   [_project(p) for p in cv.projects],
        "awards":     [_award(a) for a in cv.awards],
    })
