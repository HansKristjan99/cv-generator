"""Default CV template — the original compact single-column layout."""

from app.schemas import Award, CurriculumVitae, Education, JobExperience, Project, SkillSection

_PREAMBLE = r"""\documentclass[10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage[left=1.2cm,top=1.2cm,right=1.2cm,bottom=1.0cm]{geometry}
\usepackage[hidelinks]{hyperref}
\usepackage{parskip}
\usepackage{xcolor}
\pagestyle{empty}
\setlength{\parskip}{0pt}
\newcommand{\cvsection}[1]{\vspace{8pt}{\large \textbf{#1}}\\[-5pt]{\color{black!35}\hrule height 0.4pt}\vspace{5pt}}
\newcommand{\cventry}[4]{\textbf{#1} \hfill #2\\\textit{#3} \hfill #4}
\newenvironment{cvitemize}{\begin{list}{$\bullet$}{\setlength{\itemsep}{0pt}\setlength{\topsep}{2pt}\setlength{\parsep}{1.5pt}\setlength{\leftmargin}{14pt}}}{\end{list}}
\begin{document}
\small
"""

_ESCAPE = str.maketrans({
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
})


def _e(s: str) -> str:
    return s.translate(_ESCAPE)


def _dates(start: str, end: str) -> str:
    return f"{_e(start)} -- {_e(end)}"


def _job(j: JobExperience) -> str:
    header = (
        f"\\cventry{{{_e(j.company)}}}{{{_e(j.location)}}}"
        f"{{{_e(j.position)}}}{{{_dates(j.start_date, j.end_date)}}}"
    )
    if not j.bullets:
        return header
    bullets = "\n".join(f"    \\item {b}" for b in j.bullets)
    return f"{header}\n\\begin{{cvitemize}}\n{bullets}\n\\end{{cvitemize}}"


def _edu(e: Education) -> str:
    out = (
        f"\\cventry{{{_e(e.institution)}}}{{{_e(e.location)}}}"
        f"{{{_e(e.degree)}}}{{{_dates(e.start_date, e.end_date)}}}"
    )
    extras = []
    if e.thesis:
        extras.append(f"\\textbf{{Thesis:}} {e.thesis}.")
    if e.coursework:
        extras.append(f"\\textbf{{Coursework:}} {e.coursework}.")
    if e.gpa:
        extras.append(f"\\textbf{{GPA:}} {_e(e.gpa)}.")
    if extras:
        out += "\\\\[2pt]\n{\\footnotesize " + " ".join(extras) + "}"
    return out


def _skill(s: SkillSection) -> str:
    return f"\\textbf{{{_e(s.title)}:}} {s.items}"


def _project(p: Project) -> str:
    line = f"\\textbf{{{_e(p.name)}}} --- {p.description}"
    if p.url:
        line += f" \\href{{{p.url}}}{{{_e(p.url)}}}"
    return line


def _award(a: Award) -> str:
    parts = [a.title]
    if a.issuer:
        parts.append(_e(a.issuer))
    if a.date:
        parts.append(_e(a.date))
    return " --- ".join(parts)


def _section(title: str, entries: list[str], sep: str) -> str:
    return f"\\cvsection{{{title}}}\n" + sep.join(entries)


def cv_to_latex(cv: CurriculumVitae) -> str:
    contact = [_e(cv.location), f"\\href{{mailto:{cv.email}}}{{{_e(cv.email)}}}"]
    if cv.phone:
        contact.append(_e(cv.phone))
    for link in cv.links:
        contact.append(f"\\href{{{link}}}{{{_e(link)}}}")

    header = (
        "\\begin{center}\n"
        f"    {{\\LARGE \\textbf{{{_e(cv.name)}}}}}\\\\[5pt]\n"
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
