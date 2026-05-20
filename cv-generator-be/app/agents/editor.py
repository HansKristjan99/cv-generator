"""EditorAgent — second pass: hiring-manager review + LaTeX polish + hard page-count enforcement.

Receives rendered LaTeX + the compiled PDF, returns a polished LaTeX source whose
final PDF matches the writer's `target_pages`. Over-target is rejected; under-target
is accepted. Falls back to the original LaTeX if the model's polished version ever
fails to compile.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.schemas import PolishedCv
from app.services.latex import CompileResult, compile_latex_to_pdf
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

MAX_EDITOR_ITERATIONS = 6

SYSTEM_PROMPT = (
    "You are a senior hiring manager AND a LaTeX-literate copy editor. You are "
    "given a candidate's CV rendered to LaTeX, the compiled PDF, the target job "
    "description, and a HARD target page count. Your job is to produce a polished "
    "LaTeX source whose rendered PDF satisfies the target page count and reads as "
    "natural, hiring-manager-friendly prose.\n\n"
    "HARD RULES (non-negotiable):\n"
    " - PRESERVE EVERY FACT, NUMBER, DATE, EMPLOYER, AND TITLE EXACTLY. Do not "
    "invent achievements, inflate metrics, or change dates. You may rephrase but "
    "not falsify.\n"
    " - PRESERVE PERCENTAGES AND OTHER NUMERIC TOKENS — a very common bug is "
    "losing the '%' sign because it is a LaTeX comment character. Always escape "
    "as '\\%'. Audit every number after each edit.\n"
    " - FIX LATEX ESCAPE BUGS: '&' → '\\&', '%' → '\\%', '$' → '\\$', '#' → '\\#', "
    "'_' → '\\_', stray '{'/'}', stray '~' or '^'. Fix overfull boxes by tightening "
    "phrasing — never by shrinking font, narrowing margins, or changing geometry.\n"
    " - HIT THE TARGET PAGE COUNT EXACTLY OR UNDER. If the rendered PDF is OVER "
    "the target, you MUST trim until it fits: drop the weakest bullets first, then "
    "the weakest entire entries (oldest jobs, weakest projects), then shorten the "
    "summary. Never reduce font size or change \\geometry/\\documentclass options.\n"
    " - UNDER-TARGET IS ACCEPTABLE. If you have no truthful content to add, accept "
    "the shorter result.\n"
    " - EDITORIAL: cut keyword-stuffing, résumé theater ('spearheaded', "
    "'leveraged', 'revolutionized'), and overfit phrasing that obviously mirrors "
    "the job description verbatim. Aim for natural, evidence-dense bullets.\n\n"
    "WORKFLOW:\n"
    " 1. Read the attached PDF and the LaTeX source side by side.\n"
    " 2. Produce a revised LaTeX source in the `latex` field. Output the COMPLETE "
    "document, not a diff.\n"
    " 3. After your output is returned, you will be told the new page_count and "
    "shown the new PDF. If it does not satisfy the target, revise again.\n"
    " 4. Stop only when the PDF compiles AND page_count <= target_pages.\n\n"
    "Do NOT output explanations or commentary — only the polished `latex` field."
)


@dataclass
class EditorResult:
    latex: str
    pdf_bytes: bytes
    page_count: int
    iterations: int
    hit_target: bool


def _initial_prompt(latex: str, job_description: str | None, target_pages: int, page_count: int) -> str:
    jd = job_description.strip() if job_description else "(none provided)"
    return (
        f"=== TARGET PAGE COUNT ===\n{target_pages}\n\n"
        f"=== CURRENT PAGE COUNT ===\n{page_count}\n\n"
        f"=== JOB DESCRIPTION ===\n{jd}\n\n"
        f"=== CURRENT LATEX SOURCE ===\n{latex}"
    )


def _feedback_prompt(target_pages: int, compile_result: CompileResult) -> str:
    if not compile_result.success:
        return (
            f"Your previous LaTeX FAILED TO COMPILE. Fix the error and try again. "
            f"Error tail:\n{compile_result.error or '(no error captured)'}"
        )
    delta = compile_result.page_count - target_pages
    if delta > 0:
        return (
            f"Your previous version compiled to {compile_result.page_count} pages, "
            f"but the target is {target_pages} (over by {delta}). TRIM AGGRESSIVELY: "
            "drop the weakest bullets first, then weakest entries (oldest jobs, weakest "
            "projects), then shorten the summary. Do NOT change font size, margins, or "
            "geometry. Return the full revised LaTeX."
        )
    return (
        f"Your previous version compiled to {compile_result.page_count} pages, "
        f"which is <= target ({target_pages}). If the layout still has overfull boxes "
        "or escape bugs, fix them; otherwise return the same LaTeX as confirmation."
    )


class EditorAgent:
    """Polishes LaTeX with a hard page-count loop. Falls back to original on failure."""

    def __init__(self, client: OpenAIClient, max_iterations: int = MAX_EDITOR_ITERATIONS) -> None:
        self.client = client
        self.max_iterations = max_iterations

    def run(
        self,
        *,
        latex: str,
        initial_compile: CompileResult,
        target_pages: int,
        job_description: str | None,
    ) -> EditorResult:
        if not initial_compile.success or not initial_compile.pdf_bytes:
            logger.warning("EditorAgent: initial compile failed; skipping polish.")
            return EditorResult(
                latex=latex,
                pdf_bytes=initial_compile.pdf_bytes or b"",
                page_count=initial_compile.page_count,
                iterations=0,
                hit_target=False,
            )

        best = EditorResult(
            latex=latex,
            pdf_bytes=initial_compile.pdf_bytes,
            page_count=initial_compile.page_count,
            iterations=0,
            hit_target=initial_compile.page_count <= target_pages,
        )
        if best.hit_target:
            logger.info("EditorAgent: initial render already fits (%d pages); skipping polish.",
                        initial_compile.page_count)
            return best

        prompt = _initial_prompt(latex, job_description, target_pages, initial_compile.page_count)
        conversation_id: str | None = None

        for iteration in range(1, self.max_iterations + 1):
            logger.info("EditorAgent iteration=%d/%d", iteration, self.max_iterations)
            parsed, conversation_id = self.client.get_structured_output(
                prompt,
                PolishedCv,
                system_prompt=SYSTEM_PROMPT,
                conversation_id=conversation_id,
                attachments=[("cv.pdf", best.pdf_bytes, "application/pdf")] if iteration == 1 else None,
            )
            if parsed is None or not parsed.latex.strip():
                logger.warning("EditorAgent: empty response on iteration %d; stopping.", iteration)
                break

            compiled = compile_latex_to_pdf(parsed.latex)
            logger.info(
                "EditorAgent iter=%d compile.success=%s page_count=%d",
                iteration, compiled.success, compiled.page_count,
            )

            if compiled.success and compiled.pdf_bytes:
                hit = compiled.page_count <= target_pages
                overshoot_old = max(0, best.page_count - target_pages)
                overshoot_new = max(0, compiled.page_count - target_pages)
                if hit or overshoot_new < overshoot_old:
                    best = EditorResult(
                        latex=parsed.latex,
                        pdf_bytes=compiled.pdf_bytes,
                        page_count=compiled.page_count,
                        iterations=iteration,
                        hit_target=hit,
                    )
                if hit:
                    return best

            prompt = _feedback_prompt(target_pages, compiled)

        logger.warning(
            "EditorAgent: exhausted %d iterations; returning best (page_count=%d, target=%d).",
            self.max_iterations, best.page_count, target_pages,
        )
        return best
