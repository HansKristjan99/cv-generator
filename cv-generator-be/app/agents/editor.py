"""EditorAgent — structured-output second pass.

Edits the writer's CurriculumVitae + tweaks LayoutOverrides; the server renders
through the writer's template and recompiles until target_pages hits. The model
never writes LaTeX, so output is guaranteed to compile and CV quality stays
close to the writer's. Optional `fetch_candidate_profile` tool lets the editor
pull the candidate's stored memory when it needs to truthfully expand a thin CV.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.schemas import CurriculumVitae, LayoutOverrides, PolishedCv
from app.services.latex import CompileResult, compile_latex_to_pdf, cv_to_latex
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

MAX_EDITOR_ITERATIONS = 5

SYSTEM_PROMPT = (
    "You are a senior hiring manager AND a CV editor. You receive the candidate's "
    "CurriculumVitae JSON, the rendered PDF, the job description, and a HARD target "
    "page count. Return a `PolishedCv`: `cv` (revised CurriculumVitae) + `layout` "
    "(font_size_pt, margin_cm, section_spacing_pt). Prefer layout tweaks for small "
    "fit gaps; content edits dominate when the gap is large.\n\n"
    "INVARIANTS:\n"
    " 1. HIT target_pages exactly. Over: trim weakest bullets, then weakest entries, "
    "then shorten the summary; tighten layout too. Under: expand truthfully (deeper "
    "bullets, more responsibilities, relevant projects/awards/skills, longer summary); "
    "relax layout too.\n"
    " 2. FILL the page. A CV at 60-70% of the allowed space reads as thin — aim for "
    "~90-100% of the final allowed page.\n"
    " 3. NEVER invent facts. Preserve every number, date, employer, and title. If you "
    "can't expand truthfully, prefer layout knobs.\n"
    " 4. NO DUPLICATION. Each fact, tech, project, metric appears once. Narrow "
    "exceptions: 1-2 anchor techs in the summary, 3-5 headline techs in skills.\n\n"
    "EDITORIAL: cut keyword-stuffing, résumé theater ('spearheaded', 'leveraged'), and "
    "overfit phrasing mirroring the JD verbatim. Strip LLM tells; hiring managers "
    "reject CVs they suspect are AI-written.\n\n"
    "TOOL: if under target_pages and the visible CV has nothing left to expand, call "
    "`fetch_candidate_profile` for the candidate's full stored profile, then revise. "
    "Do NOT call when trimming, polishing, or fixing layout."
)


PROFILE_TOOL = {
    "type": "function",
    "name": "fetch_candidate_profile",
    "description": (
        "Return the candidate's full stored profile so the CV can be truthfully "
        "expanded. Call ONLY when under target_pages with no visible content left to expand."
    ),
    "parameters": {
        "type": "object",
        "properties": {"reason": {"type": "string", "description": "Why you need it."}},
        "required": ["reason"],
        "additionalProperties": False,
    },
}


def _profile_handler(memory_provider: Callable[[], str]):
    def _handle(name: str, args: dict[str, Any]) -> dict[str, Any]:
        logger.info("EditorAgent fetch_candidate_profile reason=%r", args.get("reason"))
        return {"profile": memory_provider() or "(no stored profile)"}
    return _handle


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


def _feedback_prompt(target_pages: int, c: CompileResult) -> str:
    if not c.success:
        return (
            "Previous LaTeX failed to compile — likely special characters in a text field. "
            f"Clean the affected text and resubmit. Error tail:\n{(c.error or '(no error)')[-600:]}"
        )
    head = f"Previous render: {c.page_count} pages, target {target_pages}"
    if c.page_count > target_pages:
        return f"{head} (over by {c.page_count - target_pages}). Trim weakest bullets/entries; tighten layout."
    if c.page_count < target_pages:
        return (f"{head} (under-filled — invariant #2). Expand truthfully (deeper bullets, "
                "more responsibilities, omitted projects/awards/skills, longer summary); relax layout.")
    return f"{head} (hit). Verify the final page is ≥85% full; if not, expand or relax layout."


class EditorAgent:
    """Loops structured-output edits + local rendering until page count matches."""

    def __init__(
        self,
        client: OpenAIClient,
        max_iterations: int = MAX_EDITOR_ITERATIONS,
        memory_provider: Callable[[], str] | None = None,
    ) -> None:
        self.client = client
        self.max_iterations = max_iterations
        self.memory_provider = memory_provider

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
        tools = [PROFILE_TOOL] if self.memory_provider else None
        handler = _profile_handler(self.memory_provider) if self.memory_provider else None

        for iteration in range(1, self.max_iterations + 1):
            logger.info("EditorAgent iteration=%d/%d", iteration, self.max_iterations)
            attachments = (
                [("cv.pdf", best.pdf_bytes, "application/pdf")]
                if iteration == 1 and best is not None else None
            )
            parsed, conversation_id = self.client.get_structured_output(
                prompt, PolishedCv, system_prompt=SYSTEM_PROMPT,
                conversation_id=conversation_id, attachments=attachments,
                tools=tools, tool_handler=handler,
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
                distance_best = abs(best.page_count - target_pages) if best else 10**9
                if best is None or hit or abs(compiled.page_count - target_pages) < distance_best:
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
