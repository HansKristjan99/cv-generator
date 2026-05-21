"""EditorAgent — second pass: hiring-manager review + LaTeX polish + hard invariants.

Two invariants, enforced server-side via a recompile loop:
 1. The returned LaTeX MUST compile to a PDF. We never return non-compiling .tex.
 2. The PDF should hit `target_pages` (over-target → keep trimming; under-target →
    keep expanding to fill the page) and aim for ~85-100% page utilisation.

If, after MAX_EDITOR_ITERATIONS, no polished version compiles AND the initial
render did compile, we fall back to the initial render. If even the initial
failed, EditorAgent raises — the pipeline is then responsible for failing the job
rather than persisting broken output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.schemas import PolishedCv
from app.services.latex import CompileResult, compile_latex_to_pdf
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

MAX_EDITOR_ITERATIONS = 6
_ERROR_TAIL = 800

SYSTEM_PROMPT = (
    "You are a senior hiring manager AND a LaTeX-literate copy editor. You are "
    "given a candidate's CV rendered to LaTeX, the compiled PDF, the target job "
    "description, and a HARD target page count. Your job is to produce a polished "
    "LaTeX source whose rendered PDF compiles, hits the target page count, fills "
    "the available page space, and reads as natural, human-written prose.\n\n"
    "HARD INVARIANTS (non-negotiable):\n"
    " 1. THE LATEX YOU RETURN MUST COMPILE. If the previous attempt's compile "
    "errored, fixing that error is your single highest priority — do nothing else "
    "until it compiles. Read the error tail carefully and patch the exact line "
    "indicated. Common culprits: unescaped '%', '&', '$', '#', '_', missing braces, "
    "unbalanced environments, missing packages.\n"
    " 2. HIT THE TARGET PAGE COUNT. Over-target: trim weakest bullets, then weakest "
    "entries (oldest jobs, weakest projects), then shorten the summary. NEVER reduce "
    "font size, narrow margins, or change \\geometry/\\documentclass options.\n"
    " 3. FILL THE PAGE. Under-target or a half-empty final page is BAD — it signals "
    "a thin candidate. Expand with truthful content drawn from the SOURCE TEXT, the "
    "candidate's stored profile, or the job description: add depth to bullets, "
    "surface more responsibilities for recent roles, add relevant projects/awards/"
    "skills you previously omitted, lengthen the summary to 3-4 sentences. Aim for "
    "~90-100%% of the available space on the final allowed page. Do NOT invent.\n"
    " 4. PRESERVE EVERY FACT, NUMBER, DATE, EMPLOYER, AND TITLE. You may rephrase, "
    "expand truthfully, or trim — never falsify. Watch '%' signs especially; they "
    "disappear easily because '%' is a LaTeX comment.\n\n"
    "EDITORIAL: cut keyword-stuffing, résumé theater ('spearheaded', 'leveraged', "
    "'revolutionized'), and overfit phrasing that obviously mirrors the JD verbatim. "
    "Aim for natural, evidence-dense bullets. Strip LLM tells and predictable cadence; "
    "hiring managers reject CVs they suspect are AI-written. Stay undercover.\n\n"
    "WORKFLOW:\n"
    " 1. Read the attached PDF and the LaTeX source side by side.\n"
    " 2. Produce a revised LaTeX source in the `latex` field. Output the COMPLETE "
    "document, not a diff.\n"
    " 3. The system will recompile, then tell you the new page_count and any "
    "compile errors. Revise again until all invariants hold.\n"
    "Do NOT output explanations or commentary — only the polished `latex` field."
)


@dataclass
class EditorResult:
    latex: str
    pdf_bytes: bytes
    page_count: int
    iterations: int
    hit_target: bool


def _initial_prompt(latex: str, job_description: str | None, target_pages: int, initial: CompileResult) -> str:
    jd = job_description.strip() if job_description else "(none provided)"
    status = (
        f"COMPILE STATUS: success, {initial.page_count} page(s)"
        if initial.success
        else f"COMPILE STATUS: FAILED — your first priority is to fix this.\n"
             f"ERROR TAIL:\n{(initial.error or '(no error captured)')[-_ERROR_TAIL:]}"
    )
    return (
        f"=== TARGET PAGE COUNT ===\n{target_pages}\n\n"
        f"=== {status} ===\n\n"
        f"=== JOB DESCRIPTION ===\n{jd}\n\n"
        f"=== CURRENT LATEX SOURCE ===\n{latex}"
    )


def _feedback_prompt(target_pages: int, compile_result: CompileResult) -> str:
    if not compile_result.success:
        return (
            "YOUR PREVIOUS LATEX FAILED TO COMPILE. This violates invariant #1. "
            "Fix the exact error below and resubmit — do nothing else until it compiles.\n\n"
            f"ERROR TAIL:\n{(compile_result.error or '(no error captured)')[-_ERROR_TAIL:]}"
        )
    delta = compile_result.page_count - target_pages
    if delta > 0:
        return (
            f"Previous compile: {compile_result.page_count} pages, target {target_pages} "
            f"(over by {delta}). TRIM AGGRESSIVELY: drop weakest bullets first, then "
            "weakest entries, then shorten the summary. Do NOT change font, margins, or "
            "geometry. Return the full revised LaTeX."
        )
    if compile_result.page_count < target_pages:
        return (
            f"Previous compile: {compile_result.page_count} pages, target {target_pages} "
            f"(UNDER-FILLED). The CV is too thin — invariant #3 says fill the page. "
            "EXPAND using truthful content already present in the source/profile/JD: "
            "add depth and a second clause to top bullets, surface more responsibilities "
            "for recent roles, add relevant projects/awards/skills you omitted, lengthen "
            "the summary to 3-4 sentences. Do NOT invent facts. Return the full revised LaTeX."
        )
    return (
        f"Previous compile: {compile_result.page_count} pages (matches target {target_pages}). "
        "Check that the FINAL page is well-filled (≥85% utilised). If there is a half-empty "
        "tail, expand truthfully to fill it. Also fix any remaining overfull boxes or escape "
        "bugs. Return the full revised LaTeX."
    )


class EditorAgent:
    """Polishes LaTeX. Guarantees a compiling .tex; aims for target pages and full pages."""

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
        best: EditorResult | None = None
        if initial_compile.success and initial_compile.pdf_bytes:
            best = EditorResult(
                latex=latex, pdf_bytes=initial_compile.pdf_bytes,
                page_count=initial_compile.page_count, iterations=0,
                hit_target=initial_compile.page_count == target_pages,
            )
            if best.hit_target:
                logger.info("EditorAgent: initial render already fits and fills (%d pages); skip.",
                            initial_compile.page_count)
                return best

        prompt = _initial_prompt(latex, job_description, target_pages, initial_compile)
        conversation_id: str | None = None

        for iteration in range(1, self.max_iterations + 1):
            logger.info("EditorAgent iteration=%d/%d", iteration, self.max_iterations)
            parsed, conversation_id = self.client.get_structured_output(
                prompt, PolishedCv,
                system_prompt=SYSTEM_PROMPT,
                conversation_id=conversation_id,
                attachments=(
                    [("cv.pdf", best.pdf_bytes, "application/pdf")]
                    if iteration == 1 and best is not None else None
                ),
            )
            if parsed is None or not parsed.latex.strip():
                logger.warning("EditorAgent: empty response on iteration %d; stopping.", iteration)
                break

            compiled = compile_latex_to_pdf(parsed.latex)
            logger.info("EditorAgent iter=%d compile.success=%s page_count=%d",
                        iteration, compiled.success, compiled.page_count)

            if compiled.success and compiled.pdf_bytes:
                hit = compiled.page_count == target_pages
                overshoot_new = max(0, compiled.page_count - target_pages)
                undershoot_new = max(0, target_pages - compiled.page_count)
                distance_new = overshoot_new + undershoot_new
                distance_best = (
                    abs(best.page_count - target_pages) if best is not None else 10**9
                )
                if best is None or hit or distance_new < distance_best:
                    best = EditorResult(
                        latex=parsed.latex, pdf_bytes=compiled.pdf_bytes,
                        page_count=compiled.page_count, iterations=iteration, hit_target=hit,
                    )
                if hit:
                    return best

            prompt = _feedback_prompt(target_pages, compiled)

        if best is None:
            raise RuntimeError(
                "EditorAgent: no compiling LaTeX produced after "
                f"{self.max_iterations} iterations and initial render also failed."
            )
        logger.warning("EditorAgent: exhausted %d iterations; returning best compiling render "
                       "(page_count=%d, target=%d).",
                       self.max_iterations, best.page_count, target_pages)
        return best
