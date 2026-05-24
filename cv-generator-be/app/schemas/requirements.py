"""Job-requirements gate: extract requirements once per chat and assess coverage.

Run before any CV is written. The deterministic router (in the generation
pipeline) uses `unmet_must_haves` to decide whether to ask the candidate for
missing evidence or to proceed straight to writing.
"""

from typing import Literal

from pydantic import BaseModel, Field

Importance = Literal["must_have", "nice_to_have"]


class JobRequirement(BaseModel):
    """One distinct job requirement, classified and checked against the candidate."""

    requirement: str = Field(
        ..., description="A single distinct requirement, tightly paraphrased from the job description."
    )
    importance: Importance = Field(
        ...,
        description=(
            "'must_have' if the posting frames it as required/essential/minimum; "
            "'nice_to_have' for preferred, bonus, or 'a plus' items."
        ),
    )
    met: bool = Field(
        ...,
        description=(
            "True only if the candidate's source material or stored profile already "
            "provides credible evidence for this requirement."
        ),
    )
    evidence: str = Field(
        ...,
        description=(
            "The specific candidate fact that satisfies it (role, project, skill, "
            "education), or the literal string 'Not satisfied'."
        ),
    )
    question: str = Field(
        ...,
        description=(
            "If not met, ONE targeted question asking the candidate for the specific "
            "missing evidence. Empty string when the requirement is met."
        ),
    )


class RequirementsAnalysis(BaseModel):
    """The full per-requirement analysis for a job description."""

    requirements: list[JobRequirement] = Field(
        ..., description="One entry per distinct requirement in the job description."
    )


def unmet_must_haves(analysis: RequirementsAnalysis) -> list[JobRequirement]:
    """Must-have requirements with no supporting evidence — the gate asks about these."""
    return [r for r in analysis.requirements if r.importance == "must_have" and not r.met]


def format_requirements(analysis: RequirementsAnalysis) -> str:
    """Render the analysis as a prioritized checklist for the writer prompt."""
    if not analysis.requirements:
        return ""
    ordered = sorted(analysis.requirements, key=lambda r: r.importance != "must_have")
    lines = []
    for r in ordered:
        tag = "must-have" if r.importance == "must_have" else "nice-to-have"
        status = r.evidence.strip() if r.met else "Not satisfied"
        lines.append(f"- [{tag}] {r.requirement} — {status}")
    return "\n".join(lines)
