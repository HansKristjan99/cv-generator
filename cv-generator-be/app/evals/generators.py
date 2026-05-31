"""Systems under test — implementations of the :class:`CVGenerator` protocol.

Phase 1 ships :class:`WriterAgentGenerator`: it runs the *current* production writer
path (optional requirements extraction → single-pass ``WriterAgent`` → deterministic
escape + compile) for one case and records the structured CV and the compile outcome.

Phase 2 adds a ``LangGraphGenerator`` here — same ``generate(case) -> GeneratedCV``
surface — so the runner can score both on identical inputs and report the delta.
Anything that imports this module pulls in ``openai``; the deterministic CI path does
not import it.
"""

from __future__ import annotations

import base64
import time

from app.config import MODEL
from app.evals.types import EvalCase, GeneratedCV
from app.agents import RequirementsAgent, WriterAgent
from app.schemas import CurriculumVitae, OtherMessage
from app.schemas.requirements import format_requirements
from app.services.latex import compile_latex_to_pdf, cv_to_latex
from app.services.latex_escape import escape_cv_for_latex
from app.services.openai_client import OpenAIClient


def _prompt_input(case: EvalCase) -> str:
    return (
        f"=== SOURCE CV ===\n{case.source_text}\n\n"
        f"=== JOB DESCRIPTION ===\n{case.job_description or '(none provided)'}\n"
    )


class WriterAgentGenerator:
    """Baseline generator: today's single-pass writer + compile-and-check loop."""

    name = "writer"

    def __init__(self, model: str = MODEL, *, with_requirements: bool = True) -> None:
        self.client = OpenAIClient(model)
        self.with_requirements = with_requirements

    def generate(self, case: EvalCase) -> GeneratedCV:
        started = time.monotonic()
        prompt_input = _prompt_input(case)

        # Mirror the production pipeline: extract requirements and prepend them so the
        # writer tailors to must-haves, keeping the baseline a fair comparison point.
        requirements_text = ""
        if self.with_requirements and case.job_description:
            analysis = RequirementsAgent(self.client).run(
                job_description=case.job_description,
                candidate_context=case.source_text,
                file=None,
            )
            if analysis is not None:
                requirements_text = format_requirements(analysis)
        if requirements_text:
            prompt_input = (
                "=== JOB REQUIREMENTS (cover those the candidate can support; must-haves "
                f"first) ===\n{requirements_text}\n\n{prompt_input}"
            )

        out = WriterAgent(self.client).run(prompt_input, target_pages=case.target_pages)
        content = out.response.content
        elapsed = round(time.monotonic() - started, 2)

        if isinstance(content, OtherMessage):
            # Writer declined to produce a CV; surface an empty shell so evaluators
            # record the failure rather than crashing the run.
            empty = CurriculumVitae(
                name="", location="", email="", phone=None, links=[], summary=content.text,
                experience=[], education=[], skills=[], projects=[], awards=[],
            )
            return GeneratedCV(
                cv=empty, compile_success=False, page_count=0,
                metadata={"latency_s": elapsed, "variant": "OtherMessage"},
            )

        assert isinstance(content, CurriculumVitae)
        latex = cv_to_latex(escape_cv_for_latex(content))
        compiled = compile_latex_to_pdf(latex)
        return GeneratedCV(
            cv=content,
            compile_success=compiled.success,
            page_count=compiled.page_count,
            latex=latex,
            pdf_b64=base64.b64encode(compiled.pdf_bytes).decode() if compiled.pdf_bytes else None,
            metadata={"latency_s": elapsed, "variant": "CurriculumVitae"},
        )


def get_generator(name: str) -> WriterAgentGenerator:
    """Resolve a generator by name. Phase 2 registers 'langgraph' here."""
    if name == "writer":
        return WriterAgentGenerator()
    raise ValueError(f"unknown generator: {name!r} (available: 'writer')")
