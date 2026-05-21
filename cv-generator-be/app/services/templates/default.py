"""Default CV template — the original compact single-column layout."""

from app.schemas import (
    Award,
    CurriculumVitae,
    Education,
    JobExperience,
    LayoutOverrides,
    Project,
    SkillSection,
)

DEFAULT_LAYOUT = LayoutOverrides(font_size_pt=10, margin_cm=1.2, section_spacing_pt=8)


def _preamble(layout: LayoutOverrides) -> str:
    return (
        r"\documentclass[" + str(layout.font_size_pt) + r"pt]{article}" + "\n"
        r"\usepackage[utf8]{inputenc}" + "\n"
        r"\usepackage[T1]{fontenc}" + "\n"
        r"\usepackage[english]{babel}" + "\n"
        r"\usepackage[left=" + f"{layout.margin_cm:.2f}cm"
        + r",top=" + f"{layout.margin_cm:.2f}cm"
        + r",right=" + f"{layout.margin_cm:.2f}cm"
        + r",bottom=" + f"{layout.margin_cm:.2f}cm"
        + r"]{geometry}" + "\n"
        r"\usepackage[hidelinks]{hyperref}" + "\n"
        r"\usepackage{parskip}" + "\n"
        r"\usepackage{xcolor}" + "\n"
        r"\pagestyle{empty}" + "\n"
        r"\setlength{\parskip}{0pt}" + "\n"
        r"\newcommand{\cvsection}[1]{\vspace{" + str(layout.section_spacing_pt) + r"pt}"
        + r"{\large \textbf{#1}}\\[-5pt]{\color{black!35}\hrule height 0.4pt}\vspace{5pt}}" + "\n"
        r"\newcommand{\cventry}[4]{\textbf{#1} \hfill #2\\\textit{#3} \hfill #4}" + "\n"
        r"\newenvironment{cvitemize}{\begin{list}{$\bullet$}"
        r"{\setlength{\itemsep}{0pt}\setlength{\topsep}{2pt}\setlength{\parsep}{1.5pt}"
        r"\setlength{\leftmargin}{14pt}}}{\end{list}}" + "\n"
        r"\begin{document}" + "\n"
        r"\small" + "\n"
    )

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


def cv_to_latex(cv: CurriculumVitae, layout: LayoutOverrides | None = None) -> str:
    layout = layout or DEFAULT_LAYOUT
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

    return _preamble(layout) + "\n\n".join(sections) + "\n\n\\end{document}\n"
