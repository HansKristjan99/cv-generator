"""EditorAgent — structured-output second pass.

Receives the writer's CurriculumVitae plus the initial rendered PDF, and returns a
polished `PolishedCv` (revised structured CV + layout knobs). The server renders
that through the same template the writer uses and recompiles until the result
hits the target page count.

The model never writes LaTeX directly: structured output + server-side rendering
gives us two guarantees for free:
 1. The returned LaTeX always compiles (assuming our template is correct).
 2. Editorial quality stays close to the writer's, because the editor is editing
    the same structured CV — not free-form LaTeX.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.schemas import CurriculumVitae, LayoutOverrides, PolishedCv
from app.services.latex import CompileResult, compile_latex_to_pdf, cv_to_latex
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

MAX_EDITOR_ITERATIONS = 5

SYSTEM_PROMPT = (
    "You are a senior hiring manager AND a CV editor. You receive the candidate's "
    "current structured CurriculumVitae, the rendered PDF, the target job description, "
    "and a HARD target page count. Return a polished `PolishedCv` with two fields:\n"
    " - `cv`: a revised CurriculumVitae. Edit phrasing, trim weak content, or expand "
    "with truthful detail already implied by the source. Preserve every fact, number, "
    "date, employer, and title.\n"
    " - `layout`: small knobs (`font_size_pt`, `margin_cm`, `section_spacing_pt`) that "
    "control how the server renders the CV. Use these to fine-tune fit BEFORE rewriting "
    "content, but content edits dominate when the gap is large.\n\n"
    "INVARIANTS:\n"
    " 1. HIT the target_pages exactly. Over-target: trim weakest bullets, then weakest "
    "entries (oldest jobs, weakest projects), then shorten the summary. You may also "
    "tighten the layout (smaller margins, smaller font, less section spacing). Under-"
    "target: expand truthfully (deeper bullets, more responsibilities for recent roles, "
    "relevant projects/awards/skills, longer summary). You may also relax the layout "
    "(wider margins, larger font, more spacing).\n"
    " 2. FILL the page. A CV at only 60-70% of the allowed space reads as thin. Aim "
    "for ~90-100% utilisation of the final allowed page.\n"
    " 3. NEVER invent facts. If you cannot expand truthfully, prefer layout knobs.\n"
    " 4. NO DUPLICATION. Each concrete fact, technology, project, or metric appears "
    "once. Narrow exceptions: 1-2 anchor techs in the summary, 3-5 headline techs in "
    "the skills list.\n\n"
    "EDITORIAL: cut keyword-stuffing, résumé theater ('spearheaded', 'leveraged', "
    "'revolutionized'), and overfit phrasing that obviously mirrors the JD verbatim. "
    "Strip LLM tells and predictable cadence; hiring managers reject CVs they suspect "
    "are AI-written.\n\n"
    "WORKFLOW: read the attached PDF + the CV JSON, then return PolishedCv. The server "
    "will recompile through the same template and tell you the new page_count and any "
    "compile errors. Revise until invariants hold."
)


@dataclass
class EditorResult:
    cv: CurriculumVitae
    layout: LayoutOverrides
    latex: str
    pdf_bytes: bytes
    page_count: int
    iterations: int
    hit_target: bool


def _initial_prompt(
    cv: CurriculumVitae, layout: LayoutOverrides, job_description: str | None,
    target_pages: int, initial: CompileResult,
) -> str:
    jd = job_description.strip() if job_description else "(none provided)"
    status = (
        f"COMPILE: success, {initial.page_count} page(s)"
        if initial.success else "COMPILE: FAILED (server-side template bug — flag in your reply)"
    )
    return (
        f"=== TARGET PAGE COUNT ===\n{target_pages}\n\n"
        f"=== {status} ===\n\n"
        f"=== CURRENT LAYOUT ===\n{layout.model_dump_json()}\n\n"
        f"=== JOB DESCRIPTION ===\n{jd}\n\n"
        f"=== CURRENT CV (JSON) ===\n{cv.model_dump_json()}"
    )


def _feedback_prompt(target_pages: int, compiled: CompileResult) -> str:
    if not compiled.success:
        return (
            "Your previous PolishedCv produced LaTeX that failed to compile. This is "
            "unusual — likely caused by special characters in your text. Resubmit the "
            "CV with cleaner text in the affected field. Error tail:\n"
            f"{(compiled.error or '(no error)')[-600:]}"
        )
    delta = compiled.page_count - target_pages
    if delta > 0:
        return (
            f"Previous render: {compiled.page_count} pages, target {target_pages} "
            f"(over by {delta}). Trim weakest bullets and entries; tighten layout "
            "(smaller margins, smaller font, less section spacing) if helpful."
        )
    if compiled.page_count < target_pages:
        return (
            f"Previous render: {compiled.page_count} pages, target {target_pages} "
            "(under-filled — invariant #2). Expand truthfully (deeper bullets, more "
            "responsibilities, omitted projects/awards/skills, longer summary) and/or "
            "relax the layout (wider margins, larger font, more section spacing)."
        )
    return (
        f"Previous render hit the target ({compiled.page_count} pages). Verify the "
        "FINAL page is well-filled (≥85%). If a half-empty tail remains, expand "
        "truthfully or relax the layout."
    )


class EditorAgent:
    """Loops structured-output edits + local rendering until page count matches."""

    def __init__(self, client: OpenAIClient, max_iterations: int = MAX_EDITOR_ITERATIONS) -> None:
        self.client = client
        self.max_iterations = max_iterations

    def run(
        self,
        *,
        cv: CurriculumVitae,
        layout: LayoutOverrides,
        template_slug: str,
        initial_compile: CompileResult,
        target_pages: int,
        job_description: str | None,
    ) -> EditorResult:
        best: EditorResult | None = None
        if initial_compile.success and initial_compile.pdf_bytes:
            best = EditorResult(
                cv=cv, layout=layout, latex=cv_to_latex(cv, template_slug, layout),
                pdf_bytes=initial_compile.pdf_bytes,
                page_count=initial_compile.page_count, iterations=0,
                hit_target=initial_compile.page_count == target_pages,
            )
            if best.hit_target:
                logger.info("EditorAgent: initial already hits target (%d pages); skip.",
                            initial_compile.page_count)
                return best

        prompt = _initial_prompt(cv, layout, job_description, target_pages, initial_compile)
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
            if parsed is None:
                logger.warning("EditorAgent: empty response on iter %d; stopping.", iteration)
                break

            latex = cv_to_latex(parsed.cv, template_slug, parsed.layout)
            compiled = compile_latex_to_pdf(latex)
            logger.info("EditorAgent iter=%d compile.success=%s page_count=%d",
                        iteration, compiled.success, compiled.page_count)

            if compiled.success and compiled.pdf_bytes:
                hit = compiled.page_count == target_pages
                distance_new = abs(compiled.page_count - target_pages)
                distance_best = (
                    abs(best.page_count - target_pages) if best is not None else 10**9
                )
                if best is None or hit or distance_new < distance_best:
                    best = EditorResult(
                        cv=parsed.cv, layout=parsed.layout, latex=latex,
                        pdf_bytes=compiled.pdf_bytes, page_count=compiled.page_count,
                        iterations=iteration, hit_target=hit,
                    )
                if hit:
                    return best

            prompt = _feedback_prompt(target_pages, compiled)

        if best is None:
            raise RuntimeError(
                f"EditorAgent: no compiling render after {self.max_iterations} iterations."
            )
        logger.warning("EditorAgent: exhausted %d iters; returning best (page_count=%d, target=%d).",
                       self.max_iterations, best.page_count, target_pages)
        return best
