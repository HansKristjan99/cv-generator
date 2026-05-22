"""WriterAgent — single agent that drafts a CV and self-corrects via a compile tool.

The writer is the only LLM call in the CV pipeline. The required page count is
chosen by the user (stored on the CvSession) and passed in per run — the model
does not decide length. The writer drafts a CurriculumVitae, then uses the
`compile_cv` tool to render it to PDF and read back the page count (plus the
rendered PDF, which the client attaches so the model can see its own work). It
iterates until the render hits the required page count, then returns the final
CV. Free-text fields are escaped for LaTeX deterministically on the server, so
the model writes plain text only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.writer_guide import CV_GUIDE
from app.schemas import CurriculumVitae, CVWriterResponse
from app.services.latex import compile_latex_to_pdf, cv_to_latex
from app.services.latex_escape import escape_cv_for_latex
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

# Enough parse rounds for several compile/adjust cycles plus a final answer.
_MAX_TOOL_ITERATIONS = 7


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
    "use 'MMM YYYY' dates, keep bullets to ONE printed line, and order each list "
    "most-relevant-first. Never invent facts not present in the source material or "
    "the stored profile.\n\n"
    "NO DUPLICATION. Each concrete fact (employer, project, achievement, technology, "
    "metric, award) should appear exactly once on the CV. If the same React project "
    "is in both 'experience' and 'projects', pick the section where it lands harder "
    "and drop the other mention. If a technology is already evident from a bullet, "
    "don't repeat it in the skills list unless it's a top headline skill. Narrow, "
    "well-known exceptions where repetition genuinely helps the reader: (a) the "
    "summary may name 1-2 anchor technologies that also appear in bullets, (b) the "
    "skills list may name the candidate's top 3-5 headline technologies even if "
    "they're embedded in bullets — these act as a scannable index for recruiters. "
    "Beyond that, prefer pruning duplicates over padding.\n\n"
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
    "PAGE LENGTH (a REQUIRED page count is given to you each turn — obey it exactly):\n"
    "You do NOT choose the length. The user picks it; it is stated as 'REQUIRED CV "
    "LENGTH'. The CV must render to exactly that many pages.\n\n"
    "COMPILE-AND-CHECK LOOP (REQUIRED for every CurriculumVitae):\n"
    "You have a `compile_cv` tool that renders a CV to PDF and returns its "
    "`page_count` and `fits_target`, and attaches the rendered PDF so you can SEE "
    "the result. You MUST use it before returning any CurriculumVitae:\n"
    " 1. Draft the CV sized to the budget for the required length.\n"
    " 2. Call `compile_cv` with the full draft.\n"
    " 3. Read `page_count` and look at the attached PDF:\n"
    "      * page_count > required → trim the weakest bullets, then the weakest "
    "entries, then shorten the summary; tighten before you cut substance.\n"
    "      * final page < ~85% full (thin) → expand truthfully (deeper bullets, more "
    "responsibilities, relevant projects/awards/skills, longer summary). Never invent.\n"
    " 4. Call `compile_cv` again after each revision. Only return your final "
    "CurriculumVitae once `fits_target` is true (or you have genuinely run out of "
    "truthful edits after several attempts).\n"
    "Do NOT call `compile_cv` for QuestionsToImproveCv or OtherMessage responses.\n\n"
    "CONTENT BUDGET (draft to the row matching the required length, then let the "
    "compile loop fine-tune the fit):\n"
    " - 1 page:\n"
    "     * summary: 1-2 sentences (≤ 35 words)\n"
    "     * experience: up to 3 roles total; most recent role 3-4 bullets, older 2-3\n"
    "     * education: up to 2 entries; no thesis/coursework unless directly relevant\n"
    "     * skills: 2-3 grouped rows, ≤ 12 items per row\n"
    "     * projects: 0-2 entries (only if they outperform a job bullet or you have no "
    "industry experience), one short sentence each\n"
    "     * awards: 0-2 entries; omit the section entirely if weak\n"
    " - 2 pages:\n"
    "     * summary: 2-3 sentences (≤ 60 words)\n"
    "     * experience: up to 5 roles; top 2 get 4-5 bullets, the rest 2-3\n"
    "     * education: up to 3 entries; thesis/coursework allowed when relevant\n"
    "     * skills: 3-5 grouped rows, ≤ 14 items per row\n"
    "     * projects: 0-4 entries, one short sentence each\n"
    "     * awards: 0-4 entries\n"
    " - 3 pages: budget freely, but every entry must earn its line.\n\n"
    "Every bullet MUST fit on a single printed line. Aim for ≤ 22 words per bullet; "
    "split or shorten anything longer.\n\n"
    "TEXT FORMATTING:\n"
    "Write every field as plain prose. Do NOT use LaTeX commands, markdown, HTML, or "
    "any character escaping — the server escapes special characters (& % $ # _ { } "
    "~ ^ \\) deterministically before rendering. Write '50%' not '50\\%', 'Ben & "
    "Jerry's' not 'Ben \\& Jerry's'.\n\n"
    + CV_GUIDE
)


def _compile_tool_schema() -> dict[str, Any]:
    """A `compile_cv` function tool whose parameters are the CurriculumVitae schema."""
    return {
        "type": "function",
        "name": "compile_cv",
        "description": (
            "Render a candidate CV to PDF and return its page count so you can check "
            "it against the required length before finalizing. Pass the full CV as plain "
            "text (the server escapes LaTeX characters for you). The rendered PDF is "
            "attached to the next turn so you can review the layout."
        ),
        "parameters": CurriculumVitae.model_json_schema(),
    }


def _compile_handler(template_slug: str, target_pages: int):
    def _handle(name: str, args: dict[str, Any]):
        try:
            cv = CurriculumVitae.model_validate(args)
        except Exception as exc:
            logger.warning("compile_cv received invalid CV args: %s", exc)
            return {"success": False, "error": f"Invalid CV payload: {exc}"}
        latex = cv_to_latex(escape_cv_for_latex(cv), template_slug)
        result = compile_latex_to_pdf(latex)
        payload: dict[str, Any] = {
            "success": result.success,
            "page_count": result.page_count,
            "required_pages": target_pages,
            "fits_target": result.success and result.page_count == target_pages,
        }
        if not result.success:
            payload["error"] = (result.error or "(no error)")[-600:]
        logger.info(
            "compile_cv: success=%s page_count=%d required=%d",
            result.success, result.page_count, target_pages,
        )
        return payload, (result.pdf_bytes if result.success else None)
    return _handle


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
        target_pages: int,
        template_slug: str = "default",
        file: Path | None = None,
        conversation_id: str | None = None,
    ) -> WriterResult:
        directive = (
            f"=== REQUIRED CV LENGTH ===\n"
            f"This CV MUST render to exactly {target_pages} page(s). Use the compile_cv "
            f"tool and revise until page_count == {target_pages}.\n\n"
        )
        parsed, conv_id = self.client.get_structured_output(
            directive + prompt_input,
            CVWriterResponse,
            system_prompt=SYSTEM_PROMPT,
            file=file,
            conversation_id=conversation_id,
            tools=[_compile_tool_schema()],
            tool_handler=_compile_handler(template_slug, target_pages),
            max_tool_iterations=_MAX_TOOL_ITERATIONS,
        )
        if parsed is None:
            raise RuntimeError("WriterAgent: model returned no parsed output.")
        logger.info("WriterAgent done variant=%s", type(parsed.content).__name__)
        return WriterResult(response=parsed, conversation_id=conv_id)
