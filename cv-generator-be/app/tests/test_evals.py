"""Per-push eval-harness tests — fully hermetic (no network, no pdflatex, no API key).

These pin the *evaluator logic* against two recorded fixtures: a clean CV that should
pass every deterministic check, and a deliberately flawed CV that should trip the
specific checks it violates. This is what runs on every push: if a future change to
an evaluator (or to the schema it reads) breaks the gate, CI catches it here without
spending a cent on the LLM. The live, paid eval runs separately on demand/nightly.

Only ``app.evals.types``/``deterministic``/``dataset`` are imported — none pull in
``openai`` — so the suite stays importable with zero credentials.
"""

from __future__ import annotations

import pytest

from app.evals.dataset import load_cases, load_fixture
from app.evals.deterministic import run_deterministic
from app.evals.types import EvalCase, MustHaveGroup


def _results(case: EvalCase, fixture_name: str) -> dict[str, object]:
    gen = load_fixture(fixture_name)
    return {r.dimension: r for r in run_deterministic(case, gen)}


@pytest.fixture
def case() -> EvalCase:
    """A minimal case whose must-haves the GOOD fixture satisfies and the BAD one mostly does not."""
    return EvalCase(
        id="unit",
        source_text="(unit test)",
        job_description="(unit test)",
        target_pages=1,
        must_haves=[
            MustHaveGroup(label="Frontend", keywords=["react", "typescript"]),
            MustHaveGroup(label="Backend/APIs", keywords=["rest", "graphql", "lambda"]),
            MustHaveGroup(label="Infra", keywords=["kubernetes", "ci/cd"]),
        ],
    )


def test_good_fixture_passes_every_deterministic_check(case: EvalCase) -> None:
    results = _results(case, "good_cv")
    failed = {dim: r.detail for dim, r in results.items() if not r.passed}  # type: ignore[attr-defined]
    assert not failed, f"good fixture unexpectedly failed: {failed}"


def test_bad_fixture_fails_page_fit(case: EvalCase) -> None:
    # Recorded at 2 pages against a 1-page target.
    assert _results(case, "bad_cv")["page_fit"].passed is False  # type: ignore[attr-defined]


def test_bad_fixture_flags_unanchored_skills(case: EvalCase) -> None:
    r = _results(case, "bad_cv")["skills_anchored"]
    assert r.passed is False  # type: ignore[attr-defined]
    joined = " ".join(r.findings).lower()  # type: ignore[attr-defined]
    assert "rust" in joined and "scala" in joined


def test_bad_fixture_flags_unquantified_bullets(case: EvalCase) -> None:
    # One of two bullets has no number → ratio 0.5 is the boundary; the duty bullet must be flagged.
    r = _results(case, "bad_cv")["quantified_bullets"]
    assert any("various frontend and backend" in f.lower() for f in r.findings)  # type: ignore[attr-defined]


def test_bad_fixture_flags_summary_metric_restatement(case: EvalCase) -> None:
    r = _results(case, "bad_cv")["no_duplicate_metrics"]
    assert r.passed is False  # type: ignore[attr-defined]
    assert r.score == 0.0  # type: ignore[attr-defined]


def test_must_have_coverage_discriminates(case: EvalCase) -> None:
    good = _results(case, "good_cv")["must_have_coverage"]
    bad = _results(case, "bad_cv")["must_have_coverage"]
    assert good.score > bad.score  # type: ignore[attr-defined]
    assert good.passed is True  # type: ignore[attr-defined]


def test_dataset_loads_and_is_nonempty() -> None:
    cases = load_cases()
    assert len(cases) >= 2
    assert all(c.id and c.source_text for c in cases)
    # Every must-have group must carry at least one keyword, or coverage is meaningless.
    for c in cases:
        for g in c.must_haves:
            assert g.keywords, f"{c.id}: must-have '{g.label}' has no keywords"
