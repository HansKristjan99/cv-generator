"""Default CV template — compact single-column layout.

Free-text fields on the input CurriculumVitae are assumed to be already escaped
for LaTeX by ``app.services.latex_escape.escape_cv_for_latex``. URL-position
values (email, links, project.url) come in raw and are escaped here only where
used as display text inside ``\\href{URL}{display}``.
"""

from app.schemas import (
    Award,
    CurriculumVitae,
    Education,
    JobExperience,
    Project,
    SkillSection,
)
from app.config import (
    DEFAULT_TEMPLATE_FONT_PT,
    DEFAULT_TEMPLATE_MARGIN_CM,
    DEFAULT_TEMPLATE_SECTION_SPACING_PT,
)
from app.services.latex_escape import escape_tex

_PREAMBLE = (
    rf"\documentclass[{DEFAULT_TEMPLATE_FONT_PT}pt]{{article}}" + "\n"
    r"\usepackage[utf8]{inputenc}" + "\n"
    r"\usepackage[T1]{fontenc}" + "\n"
    r"\usepackage[english]{babel}" + "\n"
    rf"\usepackage[left={DEFAULT_TEMPLATE_MARGIN_CM:.2f}cm,"
    rf"top={DEFAULT_TEMPLATE_MARGIN_CM:.2f}cm,"
    rf"right={DEFAULT_TEMPLATE_MARGIN_CM:.2f}cm,"
    rf"bottom={DEFAULT_TEMPLATE_MARGIN_CM:.2f}cm]{{geometry}}" + "\n"
    r"\usepackage[hidelinks]{hyperref}" + "\n"
    r"\usepackage{parskip}" + "\n"
    r"\usepackage{xcolor}" + "\n"
    r"\pagestyle{empty}" + "\n"
    r"\setlength{\parskip}{0pt}" + "\n"
    rf"\newcommand{{\cvsection}}[1]{{\vspace{{{DEFAULT_TEMPLATE_SECTION_SPACING_PT}pt}}"
    r"{\large \textbf{#1}}\\[-5pt]{\color{black!35}\hrule height 0.4pt}\vspace{5pt}}" + "\n"
    r"\newcommand{\cventry}[4]{\textbf{#1} \hfill #2\\\textit{#3} \hfill #4}" + "\n"
    r"\newenvironment{cvitemize}{\begin{list}{$\bullet$}"
    r"{\setlength{\itemsep}{0pt}\setlength{\topsep}{2pt}\setlength{\parsep}{1.5pt}"
    r"\setlength{\leftmargin}{14pt}}}{\end{list}}" + "\n"
    r"\begin{document}" + "\n"
    r"\small" + "\n"
)


def _dates(start: str, end: str) -> str:
    return f"{start} -- {end}"


def _job(j: JobExperience) -> str:
    header = (
        f"\\cventry{{{j.company}}}{{{j.location}}}"
        f"{{{j.position}}}{{{_dates(j.start_date, j.end_date)}}}"
    )
    if not j.bullets:
        return header
    bullets = "\n".join(f"    \\item {b}" for b in j.bullets)
    return f"{header}\n\\begin{{cvitemize}}\n{bullets}\n\\end{{cvitemize}}"


def _edu(e: Education) -> str:
    out = (
        f"\\cventry{{{e.institution}}}{{{e.location}}}"
        f"{{{e.degree}}}{{{_dates(e.start_date, e.end_date)}}}"
    )
    extras = []
    if e.thesis:
        extras.append(f"\\textbf{{Thesis:}} {e.thesis}.")
    if e.coursework:
        extras.append(f"\\textbf{{Coursework:}} {e.coursework}.")
    if e.gpa:
        extras.append(f"\\textbf{{GPA:}} {e.gpa}.")
    if extras:
        out += "\\\\[2pt]\n{\\footnotesize " + " ".join(extras) + "}"
    return out


def _skill(s: SkillSection) -> str:
    return f"\\textbf{{{s.title}:}} {s.items}"


def _project(p: Project) -> str:
    line = f"\\textbf{{{p.name}}} --- {p.description}"
    if p.url:
        line += f" \\href{{{p.url}}}{{{escape_tex(p.url)}}}"
    return line


def _award(a: Award) -> str:
    parts = [a.title]
    if a.issuer:
        parts.append(a.issuer)
    if a.date:
        parts.append(a.date)
    return " --- ".join(parts)


def _section(title: str, entries: list[str], sep: str) -> str:
    return f"\\cvsection{{{title}}}\n" + sep.join(entries)


def cv_to_latex(cv: CurriculumVitae) -> str:
    contact = [cv.location, f"\\href{{mailto:{cv.email}}}{{{escape_tex(cv.email)}}}"]
    if cv.phone:
        contact.append(cv.phone)
    for link in cv.links:
        contact.append(f"\\href{{{link}}}{{{escape_tex(link)}}}")

    header = (
        "\\begin{center}\n"
        f"    {{\\LARGE \\textbf{{{cv.name}}}}}\\\\[5pt]\n"
        f"    {' \\textbullet\\ '.join(contact)}\n"
        "\\end{center}\n"
        "\\vspace{4pt}\n\n"
        f"{cv.summary}"
    )

    sections: list[str] = [header]
    if cv.experience:
        sections.append(_section("Experience", [_job(j) for j in cv.experience], "\n\n\\vspace{5pt}\n\n"))
    if cv.education:
        sections.append(_section("Education", [_edu(e) for e in cv.education], "\n\n\\vspace{4pt}\n\n"))
    if cv.skills:
        sections.append(_section("Skills", [_skill(s) for s in cv.skills], "\\\\[3pt]\n"))
    if cv.projects:
        sections.append(_section("Projects", [_project(p) for p in cv.projects], "\\\\[3pt]\n"))
    if cv.awards:
        sections.append(_section("Awards and Achievements", [_award(a) for a in cv.awards], "\\\\[3pt]\n"))

    return _PREAMBLE + "\n\n".join(sections) + "\n\n\\end{document}\n"
