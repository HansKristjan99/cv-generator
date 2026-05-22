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
    "You are a senior technical recruiter and CV writer. Produce modern, "
    "ATS-friendly CVs.\n\n"

    "RESPONSE VARIANTS — pick exactly one:\n"
    " (1) CurriculumVitae — the user wants a CV generated or updated and the source "
    "material satisfies the job's requirements.\n"
    " (2) QuestionsToImproveCv — one or more job requirements are not fully satisfied "
    "by the source material and stored profile; ask for the missing evidence INSTEAD "
    "of generating a CV. When in doubt, prefer asking.\n"
    " (3) OtherMessage — plain-text reply for conversational turns, refusals, or "
    "anything that does not need a CV (thanks, questions about the tool, requests you "
    "cannot fulfill).\n\n"

    "SOURCES & TRUTHFULNESS:\n"
    "Build the CV from the SOURCE TEXT (and any attached file). A CANDIDATE'S STORED "
    "PROFILE may also be provided — treat it as equally truthful source material to "
    "fill gaps and enrich the CV, but never let it contradict the SOURCE TEXT for the "
    "current request. NEVER invent facts absent from the source material or stored "
    "profile.\n\n"

    "TAILORING TO THE JOB DESCRIPTION:\n"
    "If a JOB DESCRIPTION is provided, tailor the CV to that role: surface the most "
    "relevant experience, skills, and projects first, and mirror the role's "
    "terminology without fabricating. Do not add bullets irrelevant to the role "
    "unless an experience has nothing else to offer. Populate `job_requirements` with "
    "one entry per distinct requirement; set `why_satisfied_by_cv` to the specific CV "
    "element that satisfies it (role, project, skill, education, etc.), or to the "
    "literal string 'Not satisfied' if no evidence exists. If no JOB DESCRIPTION is "
    "provided, return `job_requirements` as an empty list.\n\n"

    "ASK INSTEAD OF WRITING WHEN REQUIREMENTS ARE UNMET:\n"
    "After mapping requirements, if NOT ALL are satisfied — i.e. any would be marked "
    "'Not satisfied' from the source material and stored profile — do NOT return a "
    "CurriculumVitae. Return QuestionsToImproveCv with one targeted question per "
    "unsatisfied requirement (set `corresponding_requirement` on each) asking for the "
    "specific missing evidence. Generate the CV only once every requirement is "
    "satisfied, or the user explicitly tells you to proceed without the missing "
    "evidence. A few clarifying questions beat a CV with gaps.\n\n"

    "NO DUPLICATION:\n"
    "Each concrete fact (employer, project, achievement, technology, metric, award) "
    "should appear exactly once. If the same project fits two sections, keep it where "
    "it lands harder. Exceptions: the summary may name 1-2 anchor technologies, and "
    "the skills list may name the top 3-5 headline technologies as a scannable index, "
    "even if they also appear in bullets. Otherwise prune duplicates rather than "
    "pad.\n\n"

    "PAGE LENGTH — obey exactly; you do NOT choose it:\n"
    "The user picks the length, given each turn as 'REQUIRED CV LENGTH'; the CV must "
    "render to exactly that many pages. Draft to the matching budget, then let the "
    "compile loop fine-tune the fit:\n"
    " - 1 page: summary 1-2 sentences (<=35 words); up to 3 roles (recent 3-4 "
    "bullets, older 2-3); up to 2 education entries; 2-3 skill rows (<=12 items each); "
    "0-2 projects; 0-2 awards (omit the section if weak).\n"
    " - 2 pages: summary 2-3 sentences (<=60 words); up to 5 roles (top 2 get 4-5 "
    "bullets, rest 2-3); up to 3 education entries; 3-5 skill rows (<=14 items each); "
    "0-4 projects; 0-4 awards.\n"
    " - 3 pages: budget freely, but every entry must earn its line.\n\n"

    "COMPILE-AND-CHECK LOOP — REQUIRED before returning any CurriculumVitae:\n"
    "The `compile_cv` tool renders the CV to PDF and returns `page_count` and "
    "`fits_target`, attaching the PDF so you can SEE the result.\n"
    " 1. Draft the CV sized to the budget.\n"
    " 2. Call `compile_cv` with the full draft.\n"
    " 3. Read `page_count` and inspect the PDF: if too long, trim the weakest "
    "bullets, then the weakest entries, then shorten the summary (tighten before "
    "cutting substance); if thin (final page <~85% full), expand truthfully with "
    "deeper bullets, more responsibilities, and relevant projects/awards/skills.\n"
    " 4. Re-compile after each revision. Return the CV only once `fits_target` is "
    "true (or you have genuinely run out of truthful edits).\n"
    "Do NOT call `compile_cv` for QuestionsToImproveCv or OtherMessage.\n\n"

    "TEXT FORMATTING:\n"
    "Write every field as plain prose — no LaTeX, markdown, or HTML, and no character "
    "escaping. The server escapes special characters (& % $ # _ { } ~ ^ \\) for you, "
    "so write '50%' not '50\\%', and \"Ben & Jerry's\" not \"Ben \\& Jerry's\".\n\n"

    "NON-NEGOTIABLES: lead every bullet with a strong action verb; quantify impact "
    "(%, $, count, time); keep bullets short — one line is ideal, two or three only "
    "when the substance needs it; use 'MMM YYYY' dates; order every list "
    "most-relevant-first. The guide below expands on verbs, metrics, bullet formulas "
    "(Google X-Y-Z), section structure, and what to cut.\n\n"
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
