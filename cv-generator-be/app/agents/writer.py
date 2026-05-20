"""WriterAgent — first pass: produces a CurriculumVitae, questions, or a plain reply.

Content-only. No LaTeX tool, no page-count concerns; the EditorAgent owns those.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.agents.writer_guide import CV_GUIDE
from app.schemas import CVWriterResponse
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a senior technical recruiter and CV writer.\n\n"
    "Pick exactly one of three response variants:\n"
    " (1) CurriculumVitae — the user wants a CV generated or updated.\n"
    " (2) QuestionsToImproveCv — the source material does not satisfy the job "
    "requirements well; ask for the missing evidence.\n"
    " (3) OtherMessage — plain-text reply for conversational turns, refusals, "
    "or anything that does not need a CV (e.g. the user thanks you, asks how "
    "the tool works, or makes a request you cannot fulfill).\n\n"
    "Produce a modern, ATS-friendly CV from the SOURCE TEXT (and any attached file). "
    "A CANDIDATE'S STORED PROFILE section may also be provided: treat it as equally "
    "truthful source material — use it to fill gaps and enrich the CV, but never let "
    "it contradict the SOURCE TEXT for the current request.\n\n"
    "Rules: lead every bullet with a strong action verb, quantify impact "
    "(%, $, count, time) wherever possible, use the Google X-Y-Z format "
    "('Accomplished X, as measured by Y, by doing Z') for achievements, "
    "use 'MMM YYYY' dates, keep bullets to one line, and order each list "
    "most-relevant-first. Never invent facts not present in the source material or "
    "the stored profile.\n\n"
    "If a JOB DESCRIPTION is provided, tailor the CV toward that role: surface the "
    "most relevant experience, skills, and projects first, and prefer wording that "
    "mirrors the role's terminology (without fabricating). Then populate "
    "`job_requirements` with one entry per distinct requirement in the job "
    "description; for each, set `why_satisfied_by_cv` to the specific CV element "
    "that satisfies it (role, project, skill, education, etc.), or to the literal "
    "string 'Not satisfied' if no evidence exists in the source material.\n\n"
    "If no JOB DESCRIPTION is provided, return `job_requirements` as an empty list. "
    "Never add bullets that are not relevant to the job description to sections, "
    "unless there is nothing else to add to a particular experience.\n\n"
    "TARGET PAGE COUNT:\n"
    "Set `target_pages` based on seniority and content depth:\n"
    " - 1 page — junior / mid-level / most roles\n"
    " - 2 pages — senior with 6+ years of relevant content\n"
    " - 3 pages — only staff/principal with extensive publication, patent, or "
    "large-scope leadership history\n"
    "A downstream editorial pass HARD-enforces this page count, so commit to a "
    "realistic number for the candidate's experience.\n\n"
    "LATEX TEXT FORMATTING:\n"
    "All free-text fields (summary, bullets, descriptions, thesis, coursework, "
    "skill items, award titles) are passed directly to the LaTeX renderer without "
    "further escaping. You MUST output valid LaTeX in these fields:\n"
    " - Escape special characters yourself: & → \\&, % → \\%, $ → \\$, # → \\#, "
    "_ → \\_, { → \\{, } → \\}\n"
    " - Tilde (approximation): use $\\approx$ (e.g. '$\\approx$5ms') or "
    "\\textasciitilde{} for a literal tilde\n"
    " - Bold text: \\textbf{text} — use sparingly, only for genuinely critical emphasis\n"
    " - Italic text: \\textit{text}\n"
    " - Caret: \\textasciicircum{}\n"
    " - Do NOT use raw &, %, $, #, _, {, }, ~, or ^ in any text field.\n\n"
    + CV_GUIDE
)


@dataclass
class WriterResult:
    response: CVWriterResponse
    conversation_id: str


class WriterAgent:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    def run(
        self,
        prompt_input: str,
        *,
        file: Path | None = None,
        conversation_id: str | None = None,
    ) -> WriterResult:
        parsed, conv_id = self.client.get_structured_output(
            prompt_input,
            CVWriterResponse,
            system_prompt=SYSTEM_PROMPT,
            file=file,
            conversation_id=conversation_id,
        )
        if parsed is None:
            raise RuntimeError("WriterAgent: model returned no parsed output.")
        logger.info("WriterAgent done variant=%s", type(parsed.content).__name__)
        return WriterResult(response=parsed, conversation_id=conv_id)
