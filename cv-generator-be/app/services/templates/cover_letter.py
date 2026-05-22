"""Cover-letter template — a single-column business letter with a shaded name banner.

Inspired by Sid Lacy's TeX cover-letter template (gray header banner, contact line,
right-aligned sign-off). It is rebuilt with only packages present in the deployed
TeX image (the original's ``fontawesome5``/``eso-pic``/``charter`` are not installed),
so the banner is drawn with ``xcolor`` instead of ``eso-pic`` and contact icons are
dropped.

Free-text fields on the input CoverLetter are assumed to be already escaped for
LaTeX by ``app.services.latex_escape.escape_cover_letter_for_latex``. URL-position
values (email, linkedin) come in raw and are escaped here only where used as
display text inside ``\\href{URL}{display}``.
"""

import re

from app.schemas import CoverLetter
from app.services.latex_escape import escape_tex

_PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage[a4paper,top=1.5cm,bottom=2cm,left=2.2cm,right=2.2cm]{geometry}
\usepackage[dvipsnames]{xcolor}
\usepackage[hidelinks]{hyperref}
\usepackage{parskip}
\definecolor{bannergray}{RGB}{228,228,228}
\pagestyle{empty}
\setlength{\parskip}{6pt}
\setlength{\parindent}{0pt}
\begin{document}
"""


def _contact_line(cl: CoverLetter) -> str:
    parts = [cl.location, f"\\href{{mailto:{cl.email}}}{{{escape_tex(cl.email)}}}"]
    if cl.phone:
        parts.append(cl.phone)
    if cl.linkedin:
        parts.append(f"\\href{{{cl.linkedin}}}{{{escape_tex(cl.linkedin)}}}")
    return r" \quad\textbullet\quad ".join(parts)


def _header(cl: CoverLetter) -> str:
    return (
        "\\noindent\\colorbox{bannergray}{%\n"
        "\\begin{minipage}{\\dimexpr\\textwidth-2\\fboxsep\\relax}\n"
        "\\vspace{6pt}\n"
        "\\begin{center}\n"
        f"    {{\\fontsize{{26}}{{30}}\\selectfont\\scshape {cl.name}}}\\\\[6pt]\n"
        f"    {{\\small {_contact_line(cl)}}}\n"
        "\\end{center}\n"
        "\\vspace{6pt}\n"
        "\\end{minipage}%\n"
        "}"
    )


def _body(cl: CoverLetter) -> str:
    # Normalize to single blank lines between paragraphs so each becomes a LaTeX paragraph.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cl.body) if p.strip()]
    return "\n\n".join(paragraphs)


def cover_letter_to_latex(cl: CoverLetter) -> str:
    blocks: list[str] = [_header(cl), "\\vspace{18pt}", "\\today"]

    if cl.company:
        blocks.append(f"\\vspace{{2pt}}\n{cl.company}")

    blocks.append(f"\\vspace{{6pt}}\n{cl.greeting} {cl.recipient},")
    blocks.append(_body(cl))

    signoff = [f"\\vspace{{10pt}}\n{cl.closer},\\\\[26pt]", cl.name]
    if cl.title:
        signoff.append(f"\\\\\n{cl.title}")
    blocks.append("".join(signoff))

    return _PREAMBLE + "\n\n".join(blocks) + "\n\n\\end{document}\n"
