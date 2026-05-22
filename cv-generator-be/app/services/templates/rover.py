"""Rover CV template — styled two-tone layout with colored section rules.

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
\usepackage[a4paper,top=1.8cm,bottom=2.54cm,left=2.5cm,right=2.5cm]{geometry}
\usepackage[dvipsnames]{xcolor}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{parskip}
\setcounter{secnumdepth}{0}
\pdfgentounicode=1
\setlist[itemize]{noitemsep, left=0pt..1.5em}
\setlist[description]{itemsep=0pt}
\titlespacing{\subsection}{0pt}{*0}{*0}
\titlespacing{\subsubsection}{0pt}{*0}{*0}
\titleformat{\section}{\color{Sepia}\large\bfseries\uppercase}{}{}{\ruleafter}
\titleformat{\subsection}{\large\fontseries{b}\selectfont}{}{}{}
\titleformat{\subsubsection}{\normalsize\fontseries{m}\selectfont}{}{}{}
\newcommand\ruleafter[1]{#1~{\color{gray}\leaders\hrule height 0.4pt\hfill}\kern0pt}
\pagestyle{empty}
\setlength{\parskip}{0pt}
\begin{document}
"""


def _dates(start: str, end: str) -> str:
    return f"{start} -- {end}"


def _job(j: JobExperience) -> str:
    lines = [
        f"\\subsection{{{j.company} \\hfill {_dates(j.start_date, j.end_date)}}}",
        f"\\subsubsection{{{j.position} \\hfill {j.location}}}",
    ]
    if j.bullets:
        bullet_items = "\n".join(f"    \\item {b}" for b in j.bullets)
        lines.append(f"\\begin{{itemize}}\n{bullet_items}\n\\end{{itemize}}")
    return "\n".join(lines)


def _edu(e: Education) -> str:
    lines = [
        f"\\subsection{{{e.institution} $|$ {{\\normalfont\\textit{{{e.degree}}}}} \\hfill {e.end_date}}}",
    ]
    items: list[str] = []
    if e.gpa:
        items.append(f"GPA: {e.gpa}")
    if e.coursework:
        items.append(f"Related Coursework: {e.coursework}")
    if e.thesis:
        items.append(f"Thesis: {e.thesis}")
    if items:
        item_lines = "\n".join(f"    \\item {item}" for item in items)
        lines.append(f"\\begin{{itemize}}\n{item_lines}\n\\end{{itemize}}")
    return "\n".join(lines)


def _skill(s: SkillSection) -> str:
    return f"    \\item[\\textbf{{{s.title}}}] {s.items}"


def _project(p: Project) -> str:
    name_part = p.name
    if p.url:
        name_part += f" {{\\normalfont $|$ \\href{{{p.url}}}{{\\textit{{{escape_tex(p.url)}}}}}}}"
    lines = [f"\\subsection{{{name_part}}}"]
    if p.description:
        lines.append(f"\\begin{{itemize}}\n    \\item {p.description}\n\\end{{itemize}}")
    return "\n".join(lines)


def _award(a: Award) -> str:
    parts = [a.title]
    if a.issuer:
        parts.append(a.issuer)
    if a.date:
        parts = [f"[{a.date}] " + " --- ".join(parts)]
        return parts[0]
    return " --- ".join(parts)


def cv_to_latex(cv: CurriculumVitae) -> str:
    contact_parts = [cv.location, f"\\href{{mailto:{cv.email}}}{{{escape_tex(cv.email)}}}"]
    if cv.phone:
        contact_parts.append(cv.phone)
    for link in cv.links:
        contact_parts.append(f"\\href{{{link}}}{{{escape_tex(link)}}}")

    header = (
        "\\begin{center}\n"
        f"    {{\\fontsize{{28}}{{28}}\\selectfont {cv.name}}}\\\\ \\bigskip\n"
        f"    {' $|$ '.join(contact_parts)}\n"
        "\\end{center}\n\n"
        f"{cv.summary}"
    )

    blocks: list[str] = [header]

    if cv.experience:
        entries = "\n\n".join(_job(j) for j in cv.experience)
        blocks.append(f"\\section{{Experience}}\n{entries}")

    if cv.education:
        entries = "\n\n".join(_edu(e) for e in cv.education)
        blocks.append(f"\\section{{Education}}\n{entries}")

    if cv.skills:
        skill_lines = "\n".join(_skill(s) for s in cv.skills)
        blocks.append(f"\\section{{Skills}}\n\\begin{{description}}\n{skill_lines}\n\\end{{description}}")

    if cv.projects:
        entries = "\n\n".join(_project(p) for p in cv.projects)
        blocks.append(f"\\section{{Projects}}\n{entries}")

    if cv.awards:
        award_items = "\n".join(f"  \\item {_award(a)}" for a in cv.awards)
        blocks.append(
            f"\\section{{Awards \\& Achievements}}\n"
            f"\\begin{{enumerate}}[itemsep=0pt]\n{award_items}\n\\end{{enumerate}}"
        )

    return _PREAMBLE + "\n\n".join(blocks) + "\n\n\\end{document}\n"
