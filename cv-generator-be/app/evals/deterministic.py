"""Deterministic CV-quality evaluators — no network, no pdflatex, no API key.

These encode the parts of "CV quality" that are *objective* and therefore the right
thing to gate every push on: a CV either compiles, fits the page, evidences its
skills, quantifies its bullets, avoids self-duplication, and covers the job's
must-haves — or it does not. Pushing this much of quality into the cheap,
deterministic layer is the whole point: the (paid, flaky) LLM judge then only has
to cover the genuinely subjective residue.

Each evaluator is ``(EvalCase, GeneratedCV) -> EvalResult`` with a normalized
``score`` in ``[0, 1]``. ``page_fit``/``compiles`` read the *recorded* compile
result on :class:`GeneratedCV`, so they work in CI from fixtures without a LaTeX
toolchain.
"""

from __future__ import annotations

import re

from app.evals.types import EvalCase, EvalResult, GeneratedCV
from app.schemas import CurriculumVitae

# A skill counts as "evidenced" if its words show up elsewhere; these connectors are
# ignored so "Frameworks & Libraries"-style multiword skills match on their content.
_SKILL_STOPWORDS = {"and", "the", "of", "for", "with", "to", "a", "an", "&", "/", "-", "+"}
# Matches metrics like "50%", "$1.2M"→"$1.2", "2,000", "3" so we can spot a summary
# that simply restates a bullet's number.
_METRIC_RE = re.compile(r"\$?\d[\d,\.]*%?")

# Pass thresholds. These are deliberate product choices, not magic — tune against the
# eval set, not against a single CV.
SKILLS_ANCHORED_PASS = 0.85
QUANTIFIED_BULLETS_PASS = 0.5
MUST_HAVE_COVERAGE_PASS = 0.8


def _anchor_pool(cv: CurriculumVitae) -> str:
    """Lower-cased text of everything that can *evidence* a skill — i.e. the whole CV
    except the skills section itself (a skill must be backed by real content elsewhere).
    """
    parts: list[str] = [cv.summary]
    for e in cv.experience:
        parts += [e.company, e.position, *e.bullets]
    for ed in cv.education:
        parts += [ed.institution, ed.degree, ed.thesis or "", ed.coursework or ""]
    for p in cv.projects:
        parts += [p.name, p.description]
    for a in cv.awards:
        parts += [a.title, a.issuer or ""]
    return " \n ".join(parts).lower()


def _all_text(cv: CurriculumVitae) -> str:
    """Lower-cased text of the entire CV including skills — used for keyword coverage."""
    skills = " ".join(f"{s.title} {s.items}" for s in cv.skills)
    return (_anchor_pool(cv) + " \n " + skills).lower()


def _skill_items(cv: CurriculumVitae) -> list[str]:
    items: list[str] = []
    for section in cv.skills:
        items += [i.strip() for i in section.items.split(",") if i.strip()]
    return items


def _is_anchored(skill: str, pool: str) -> bool:
    """True if a skill is evidenced in the pool: either the whole phrase appears, or
    every significant word of it does (so 'AWS Lambda' matches a bullet mentioning
    AWS Lambda even if not contiguous)."""
    s = skill.lower().strip()
    if not s:
        return True
    if s in pool:
        return True
    words = [w for w in re.split(r"[\s/]+", s) if len(w) >= 3 and w not in _SKILL_STOPWORDS]
    return bool(words) and all(w in pool for w in words)


def eval_compiles(case: EvalCase, gen: GeneratedCV) -> EvalResult:
    ok = gen.compile_success
    return EvalResult(
        dimension="compiles",
        score=1.0 if ok else 0.0,
        passed=ok,
        detail="LaTeX compiled to PDF" if ok else "compilation failed",
    )


def eval_page_fit(case: EvalCase, gen: GeneratedCV) -> EvalResult:
    fits = gen.compile_success and 1 <= gen.page_count <= case.target_pages
    return EvalResult(
        dimension="page_fit",
        score=1.0 if fits else 0.0,
        passed=fits,
        detail=f"page_count={gen.page_count} target<={case.target_pages}",
        findings=[] if fits else [f"{gen.page_count} pages exceeds {case.target_pages}-page limit"],
    )


def eval_schema_complete(case: EvalCase, gen: GeneratedCV) -> EvalResult:
    """The required spine of a CV is present and non-empty."""
    cv = gen.cv
    missing = [
        name
        for name, value in (
            ("name", cv.name.strip()),
            ("email", cv.email.strip()),
            ("summary", cv.summary.strip()),
            ("experience", cv.experience),
        )
        if not value
    ]
    ok = not missing
    return EvalResult(
        dimension="schema_complete",
        score=1.0 if ok else 0.0,
        passed=ok,
        detail="all required sections present" if ok else f"missing: {', '.join(missing)}",
        findings=[f"empty required field: {m}" for m in missing],
    )


def eval_skills_anchored(case: EvalCase, gen: GeneratedCV) -> EvalResult:
    """Every listed skill must be backed by real content elsewhere in the CV."""
    items = _skill_items(gen.cv)
    if not items:
        return EvalResult(dimension="skills_anchored", score=1.0, passed=True,
                          detail="no skills listed")
    pool = _anchor_pool(gen.cv)
    unanchored = [s for s in items if not _is_anchored(s, pool)]
    ratio = 1.0 - len(unanchored) / len(items)
    return EvalResult(
        dimension="skills_anchored",
        score=round(ratio, 3),
        passed=ratio >= SKILLS_ANCHORED_PASS,
        detail=f"{len(items) - len(unanchored)}/{len(items)} skills evidenced",
        findings=[f"unanchored skill (no evidence elsewhere): {s}" for s in unanchored],
    )


def eval_quantified_bullets(case: EvalCase, gen: GeneratedCV) -> EvalResult:
    """Impact density: share of experience bullets that contain a number."""
    bullets = [b for e in gen.cv.experience for b in e.bullets]
    if not bullets:
        return EvalResult(dimension="quantified_bullets", score=1.0, passed=True,
                          detail="no experience bullets")
    quantified = [b for b in bullets if any(c.isdigit() for c in b)]
    ratio = len(quantified) / len(bullets)
    weak = [b for b in bullets if not any(c.isdigit() for c in b)]
    return EvalResult(
        dimension="quantified_bullets",
        score=round(ratio, 3),
        passed=ratio >= QUANTIFIED_BULLETS_PASS,
        detail=f"{len(quantified)}/{len(bullets)} bullets quantified",
        findings=[f"unquantified bullet: {b}" for b in weak[:5]],
    )


def eval_no_duplicate_metrics(case: EvalCase, gen: GeneratedCV) -> EvalResult:
    """The summary must characterize, not restate a bullet's metric."""
    summary_metrics = {m for m in _METRIC_RE.findall(gen.cv.summary) if any(c.isdigit() for c in m)}
    bullet_metrics = {
        m
        for e in gen.cv.experience
        for b in e.bullets
        for m in _METRIC_RE.findall(b)
        if any(c.isdigit() for c in m)
    }
    overlap = sorted(summary_metrics & bullet_metrics)
    ok = not overlap
    return EvalResult(
        dimension="no_duplicate_metrics",
        score=1.0 if ok else 0.0,
        passed=ok,
        detail="summary does not restate bullet metrics" if ok else f"restated: {', '.join(overlap)}",
        findings=[f"summary restates bullet metric '{m}'" for m in overlap],
    )


def eval_must_have_coverage(case: EvalCase, gen: GeneratedCV) -> EvalResult:
    """Fraction of the job's must-have requirements visibly evidenced in the CV."""
    if not case.must_haves:
        return EvalResult(dimension="must_have_coverage", score=1.0, passed=True,
                          detail="no must-haves declared for this case")
    text = _all_text(gen.cv)
    covered = [g for g in case.must_haves if any(k.lower() in text for k in g.keywords)]
    unmet = [g.label for g in case.must_haves if g not in covered]
    ratio = len(covered) / len(case.must_haves)
    return EvalResult(
        dimension="must_have_coverage",
        score=round(ratio, 3),
        passed=ratio >= MUST_HAVE_COVERAGE_PASS,
        detail=f"{len(covered)}/{len(case.must_haves)} must-haves evidenced",
        findings=[f"must-have not evidenced: {label}" for label in unmet],
    )


# Order matters only for report readability. Hard gates first, then content quality.
DETERMINISTIC_EVALUATORS = [
    eval_compiles,
    eval_page_fit,
    eval_schema_complete,
    eval_skills_anchored,
    eval_quantified_bullets,
    eval_no_duplicate_metrics,
    eval_must_have_coverage,
]


def run_deterministic(case: EvalCase, gen: GeneratedCV) -> list[EvalResult]:
    return [evaluator(case, gen) for evaluator in DETERMINISTIC_EVALUATORS]
