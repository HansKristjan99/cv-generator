"""Requirements gate: deterministic routing helpers."""

from app.schemas.requirements import (
    JobRequirement,
    RequirementsAnalysis,
    format_requirements,
    unmet_must_haves,
)


def _req(requirement, importance, met, question="") -> JobRequirement:
    return JobRequirement(
        requirement=requirement,
        importance=importance,
        met=met,
        evidence="Some role" if met else "Not satisfied",
        question=question,
    )


def test_unmet_must_haves_only_returns_unmet_required_items() -> None:
    analysis = RequirementsAnalysis(
        requirements=[
            _req("Python", "must_have", True),
            _req("Kubernetes", "must_have", False, question="Have you run K8s in prod?"),
            _req("GraphQL", "nice_to_have", False),  # unmet but optional → not a gate blocker
        ]
    )
    unmet = unmet_must_haves(analysis)
    assert [r.requirement for r in unmet] == ["Kubernetes"]


def test_unmet_must_haves_empty_when_all_required_met() -> None:
    analysis = RequirementsAnalysis(
        requirements=[
            _req("Python", "must_have", True),
            _req("Nice to have thing", "nice_to_have", False),
        ]
    )
    assert unmet_must_haves(analysis) == []


def test_format_requirements_orders_must_haves_first() -> None:
    analysis = RequirementsAnalysis(
        requirements=[
            _req("GraphQL", "nice_to_have", False),
            _req("Python", "must_have", True),
        ]
    )
    text = format_requirements(analysis)
    lines = text.splitlines()
    assert lines[0].startswith("- [must-have] Python")
    assert lines[1].startswith("- [nice-to-have] GraphQL — Not satisfied")
