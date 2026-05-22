"""Harvard Classic CV template — clean academic style with centered headings.

Free-text fields on the input CurriculumVitae are assumed to be already escaped
for LaTeX. URL-position values (email, links, project.url) come in raw and are
escaped here only where used as display text inside ``\\href{URL}{display}``.
"""

from app.schemas import Award, CurriculumVitae, Education, JobExperience, Project, SkillSection
from app.services.latex_escape import escape_tex

_PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage[left=1.06cm,top=1.7cm,right=1.06cm,bottom=0.49cm]{geometry}
\usepackage{hyperref}
\usepackage{enumitem}
\setlength{\parindent}{0pt}
\pagestyle{empty}
\begin{document}
"""


def _dates(start: str, end: str) -> str:
    return f"{start} -- {end}"


def _section_heading(title: str) -> str:
    return f"\\begin{{center}}\n    \\textbf{{{title}}}\n\\end{{center}}\n"


def _job(j: JobExperience) -> str:
    lines = [
        f"\\textbf{{{j.company}}} \\hfill {j.location}\n\n"
        f"\\textbf{{{j.position}}} \\hfill {_dates(j.start_date, j.end_date)}"
    ]
    if j.bullets:
        bullet_items = "\n".join(f"    \\item {b}" for b in j.bullets)
        lines.append(
            "\\begin{itemize}[noitemsep, topsep=0pt, partopsep=0pt, parsep=0pt]\n"
            f"{bullet_items}\n"
            "\\end{itemize}"
        )
    return "\n".join(lines)


def _edu(e: Education) -> str:
    lines = [f"\\textbf{{{e.institution}}} \\hfill {e.location}\n\n{e.degree}"]
    extras = []
    if e.gpa:
        extras.append(f"GPA: {e.gpa}")
    if e.thesis:
        extras.append(f"Thesis: {e.thesis}")
    if e.coursework:
        extras.append(f"Relevant Coursework: {e.coursework}")
    if extras:
        lines.append(" \\hfill " + _dates(e.start_date, e.end_date))
        lines.append("\n".join(extras))
    else:
        lines[0] += " \\hfill " + _dates(e.start_date, e.end_date)
    return "\n\n".join(lines)


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


def cv_to_latex(cv: CurriculumVitae) -> str:
    contact_parts = [cv.location, f"\\href{{mailto:{cv.email}}}{{{escape_tex(cv.email)}}}"]
    if cv.phone:
        contact_parts.append(cv.phone)
    for link in cv.links:
        contact_parts.append(f"\\href{{{link}}}{{{escape_tex(link)}}}")

    header = (
        "\\begin{center}\n"
        f"    \\textbf{{{cv.name}}}\\\\\n"
        "    \\hrulefill\n"
        "\\end{center}\n\n"
        "\\begin{center}\n"
        f"    {' \\textbullet\\ '.join(contact_parts)}\n"
        "\\end{center}\n\n"
        f"\\vspace{{0.5pt}}\n\n"
        f"{cv.summary}\n\n"
        "\\vspace{12pt}"
    )

    blocks: list[str] = [header]

    if cv.experience:
        entries = "\n\n\\vspace{12pt}\n\n".join(_job(j) for j in cv.experience)
        blocks.append(_section_heading("Experience") + entries)

    if cv.education:
        entries = "\n\n\\vspace{12pt}\n\n".join(_edu(e) for e in cv.education)
        blocks.append(_section_heading("Education") + entries)

    if cv.skills:
        skill_lines = "\n\n".join(_skill(s) for s in cv.skills)
        blocks.append(_section_heading("Skills") + skill_lines)

    if cv.projects:
        proj_lines = "\n\n".join(_project(p) for p in cv.projects)
        blocks.append(_section_heading("Projects") + proj_lines)

    if cv.awards:
        award_lines = "\n\n".join(_award(a) for a in cv.awards)
        blocks.append(_section_heading("Awards \\& Achievements") + award_lines)

    return _PREAMBLE + "\n\n\\vspace{12pt}\n\n".join(blocks) + "\n\n\\end{document}\n"
