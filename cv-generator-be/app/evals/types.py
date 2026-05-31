"""Core data types for the CV eval harness.

These types are the contract between the three moving parts of the harness:

  * a **dataset** of :class:`EvalCase` (frozen, human-authored inputs + expectations),
  * a **generator** (the system under test) that turns a case into a :class:`GeneratedCV`,
  * a set of **evaluators** that score a ``(case, generated)`` pair into
    :class:`EvalResult` rows.

The generator is expressed as the :class:`CVGenerator` protocol so the runner is
agnostic to *what* produced the CV. Phase 1 ships ``WriterAgentGenerator`` (the
current single-pass writer); Phase 2 will add a ``LangGraphGenerator`` (the
critic-loop graph) that satisfies the same protocol — no runner/evaluator changes.

Nothing in this module imports ``openai`` or the agents, so it (and the
deterministic evaluators built on it) can be imported and exercised in CI with no
network and no API key.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.schemas import CurriculumVitae


class MustHaveGroup(BaseModel):
    """One must-have requirement of a job, expressed as OR-matched keywords.

    A group counts as *covered* when ANY of its keywords appears anywhere in the
    generated CV's text. Grouping by synonyms ("python"/"php"/"go" for "backend")
    keeps the check robust to wording while staying fully deterministic — no LLM
    needed to measure job-fit coverage.
    """

    label: str = Field(..., description="Human-readable name of the requirement.")
    keywords: list[str] = Field(
        ..., description="Lower-cased keywords; the group is covered if any one appears."
    )


class EvalCase(BaseModel):
    """A single frozen, human-authored input to the CV generator.

    The ``must_haves`` are the 'golden' part: a human decides which requirements a
    good CV must visibly evidence, so coverage can be scored without a model.
    """

    id: str
    source_text: str = Field(..., description="Candidate CV text / stored-profile material.")
    job_description: str | None = Field(default=None)
    target_pages: int = Field(default=1, description="Hard page ceiling for this case.")
    must_haves: list[MustHaveGroup] = Field(default_factory=list)
    notes: str = Field(default="", description="Why this case exists / what failure mode it probes.")


class GeneratedCV(BaseModel):
    """The output of a generator for one case — the thing evaluators score.

    ``pdf_b64`` is kept off the serialized report (it is large and not needed for
    scoring); ``metadata`` carries forward-looking loop metrics (iterations,
    convergence, latency, tokens) that Phase 2's critic loop will populate and the
    process-metric evaluators will read.
    """

    cv: CurriculumVitae
    compile_success: bool = False
    page_count: int = 0
    latex: str | None = None
    pdf_b64: str | None = Field(default=None, exclude=True, repr=False)
    metadata: dict = Field(default_factory=dict)


class EvalResult(BaseModel):
    """One evaluator's verdict on one case, normalized so dimensions are comparable.

    ``score`` is always in ``[0, 1]`` (1 == perfect) so heterogeneous evaluators
    (deterministic ratios and 1-4 judge scales) aggregate cleanly. ``passed`` is the
    binary gate used by CI / regression detection; ``findings`` are the specific,
    actionable problems — these double as the runtime critic feedback in Phase 2.
    """

    dimension: str
    score: float = Field(..., ge=0.0, le=1.0)
    passed: bool
    detail: str = ""
    findings: list[str] = Field(default_factory=list)
    kind: str = Field(default="deterministic", description="'deterministic' | 'judge' | 'process'.")


class CaseReport(BaseModel):
    """All evaluator results for a single case."""

    case_id: str
    results: list[EvalResult] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)


class EvalRun(BaseModel):
    """A full run of one generator over the dataset, plus aggregates."""

    generator: str
    created_at: str
    cases: list[CaseReport] = Field(default_factory=list)

    def dimension_means(self) -> dict[str, float]:
        """Mean normalized score per dimension across all cases."""
        sums: dict[str, float] = {}
        counts: dict[str, int] = {}
        for case in self.cases:
            for r in case.results:
                sums[r.dimension] = sums.get(r.dimension, 0.0) + r.score
                counts[r.dimension] = counts.get(r.dimension, 0) + 1
        return {d: sums[d] / counts[d] for d in sums}

    def dimension_pass_rates(self) -> dict[str, float]:
        """Fraction of cases that passed, per dimension."""
        passed: dict[str, int] = {}
        counts: dict[str, int] = {}
        for case in self.cases:
            for r in case.results:
                passed[r.dimension] = passed.get(r.dimension, 0) + int(r.passed)
                counts[r.dimension] = counts.get(r.dimension, 0) + 1
        return {d: passed[d] / counts[d] for d in passed}


@runtime_checkable
class CVGenerator(Protocol):
    """The system under test. Implementations turn a case into a scored-ready CV.

    Keep this surface tiny: a name (for reports) and ``generate``. Both the current
    writer and the future LangGraph network satisfy it, which is what lets the eval
    measure the delta between them on identical inputs.
    """

    name: str

    def generate(self, case: EvalCase) -> GeneratedCV: ...
