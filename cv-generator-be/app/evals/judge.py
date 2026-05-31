"""LLM-as-judge evaluators for the subjective residue of CV quality.

The deterministic layer covers what is objective. What's left — does the writing
*read* well, is the strongest material first, is each claim actually grounded in the
source — needs a model. This module follows the judge best-practices that matter:

  * **Decomposed rubric**, not one global 1-10. Each dimension is scored 1-4 on an
    anchored scale, independently.
  * **Reasoning before the score** (CoT) via structured output, so the verdict is
    justified rather than guessed.
  * **A separate context** from generation: the judge never sees the writer's
    private reasoning, only the source, the job, and the finished CV — reducing the
    self-enhancement bias of a model grading its own in-context work.
  * **Pairwise comparison with position-bias control** for measuring deltas between
    two generators (run both A/B orders, average) — the reliable way to answer
    "did Phase 2 actually beat Phase 1?".

The same rubric is reused as the runtime critic in Phase 2: build it once, judge
offline and critique online.

Requires ``OPENAI_API_KEY``; this module is intentionally not imported by the
deterministic CI path.
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from app.config import MODEL
from app.evals.types import EvalCase, EvalResult, GeneratedCV
from app.schemas import CurriculumVitae
from app.services.openai_client import OpenAIClient

# A stronger/independent model than the generator is ideal for judging; override via
# env. Defaults to the app model so the harness runs out of the box.
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", MODEL)

JUDGE_SYSTEM = (
    "You are a meticulous, skeptical hiring manager grading a CV that was generated "
    "from a candidate's source material for a specific job. Grade ONLY what is on the "
    "page against the source provided — never reward claims you cannot trace to the "
    "source, and never penalize the CV for source facts that are simply absent. For "
    "each dimension, give your reasoning FIRST, then a 1-4 integer score using the "
    "anchors exactly. Be discriminating: reserve 4 for genuinely excellent, use 2 for "
    "mediocre. Do not be lenient."
)

_RUBRIC = (
    "DIMENSIONS (score each 1-4):\n"
    "1) grounding — every claim is supported by the SOURCE. "
    "4: nothing fabricated, all specifics traceable. 3: minor unsupported embellishment. "
    "2: several claims not in the source. 1: significant fabrication.\n"
    "2) job_fit — the most important job requirements are visibly EVIDENCED (not just "
    "name-dropped). 4: every key requirement clearly evidenced and surfaced early. "
    "3: most evidenced. 2: requirements only name-dropped. 1: poorly targeted.\n"
    "3) writing_impact — bullets lead with strong verbs and quantify impact; no vague "
    "duty bullets; no duplication between summary and bullets. 4: consistently strong. "
    "3: mostly strong. 2: many weak/vague bullets. 1: generic throughout.\n"
    "4) structure — strongest, most relevant material first; clean, scannable, "
    "appropriately dense. 4: excellent prioritization. 3: good. 2: poor ordering. "
    "1: disorganized.\n"
)


class DimensionScore(BaseModel):
    reasoning: str = Field(..., description="Concise justification, written BEFORE the score.")
    score: int = Field(..., ge=1, le=4)


class JudgeVerdict(BaseModel):
    grounding: DimensionScore
    job_fit: DimensionScore
    writing_impact: DimensionScore
    structure: DimensionScore


class PairwiseVerdict(BaseModel):
    reasoning: str = Field(..., description="Justification, written BEFORE the verdict.")
    winner: Literal["A", "B", "tie"]


def _cv_block(cv: CurriculumVitae) -> str:
    return cv.model_dump_json(indent=2)


def _context(case: EvalCase) -> str:
    return (
        f"=== SOURCE MATERIAL ===\n{case.source_text}\n\n"
        f"=== JOB DESCRIPTION ===\n{case.job_description or '(none provided)'}\n"
    )


def judge_cv(case: EvalCase, gen: GeneratedCV, client: OpenAIClient | None = None) -> list[EvalResult]:
    """Score one CV on the decomposed rubric, returning one EvalResult per dimension.

    Scores are normalized to ``[0, 1]`` as ``(score - 1) / 3`` so a 1-4 judge sits on
    the same axis as the deterministic ratios; ``passed`` is ``score >= 3``.
    """
    client = client or OpenAIClient(JUDGE_MODEL)
    prompt = (
        f"{_context(case)}\n=== GENERATED CV (JSON) ===\n{_cv_block(gen.cv)}\n\n{_RUBRIC}"
    )
    verdict, _ = client.get_structured_output(prompt, JudgeVerdict, system_prompt=JUDGE_SYSTEM)
    if verdict is None:
        raise RuntimeError("judge_cv: model returned no parsed verdict")

    results: list[EvalResult] = []
    for dim in ("grounding", "job_fit", "writing_impact", "structure"):
        ds: DimensionScore = getattr(verdict, dim)
        results.append(
            EvalResult(
                dimension=dim,
                score=(ds.score - 1) / 3.0,
                passed=ds.score >= 3,
                detail=f"score={ds.score}/4 — {ds.reasoning}",
                kind="judge",
            )
        )
    return results


def _pairwise_once(
    case: EvalCase, cv_a: CurriculumVitae, cv_b: CurriculumVitae, client: OpenAIClient
) -> str:
    prompt = (
        f"{_context(case)}\nTwo CVs were generated for this candidate and job. Decide "
        f"which is the better CV overall (grounding, job-fit, writing, structure). "
        f"Reason first, then pick.\n\n=== CV A ===\n{_cv_block(cv_a)}\n\n"
        f"=== CV B ===\n{_cv_block(cv_b)}\n"
    )
    verdict, _ = client.get_structured_output(
        prompt, PairwiseVerdict, system_prompt=JUDGE_SYSTEM,
    )
    if verdict is None:
        raise RuntimeError("pairwise: model returned no parsed verdict")
    return verdict.winner


def pairwise(
    case: EvalCase, gen_a: GeneratedCV, gen_b: GeneratedCV, client: OpenAIClient | None = None
) -> Literal["A", "B", "tie"]:
    """Compare two generators on one case, controlling for position bias by running
    BOTH orders and only declaring a winner if the two passes agree. Disagreement
    (the judge just preferred whichever came first) collapses to a tie.
    """
    client = client or OpenAIClient(JUDGE_MODEL)
    first = _pairwise_once(case, gen_a.cv, gen_b.cv, client)          # A in slot A
    second = _pairwise_once(case, gen_b.cv, gen_a.cv, client)         # A in slot B
    # Translate the swapped run back to A/B terms.
    second_in_ab = {"A": "B", "B": "A", "tie": "tie"}[second]
    if first == second_in_ab:
        return first  # type: ignore[return-value]
    return "tie"
