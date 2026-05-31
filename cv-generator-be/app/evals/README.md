# CV-quality eval harness (Phase 1)

An eval-driven test bed for CV generation. It answers one question repeatably:
**did a change make the CVs better or worse?** — so prompt/architecture changes are
judged by numbers, not vibes.

This is Phase 1: it establishes the dataset, the evaluators, the runner, and the CI
gate against **today's single-pass writer**. Phase 2 (a LangGraph generator→critic
loop) plugs into the exact same harness so the two can be compared head-to-head.

## How it fits together

```
dataset (frozen)        generator (system under test)      evaluators
EvalCase  ───────────▶  CVGenerator.generate() ─▶ GeneratedCV ─▶ deterministic + judge
cases.jsonl             WriterAgentGenerator (Phase 1)            EvalResult rows
                        LangGraphGenerator   (Phase 2)            │
                                                                  ▼
                                                          report.json / report.md
                                                          compare() → regression gate
```

The contract is `CVGenerator` (`types.py`): `name` + `generate(case) -> GeneratedCV`.
Anything satisfying it can be scored, which is what lets Phase 2 drop in with **zero**
runner or evaluator changes.

## The two evaluation layers

Quality is scored cheapest-first. As much of "good CV" as possible is pushed into the
**objective** layer; the paid LLM judge only covers the genuinely subjective residue.

### 1. Deterministic (`deterministic.py`) — no network, no API key, no LaTeX
Runs on **every push** and gates the build.

| Dimension | Checks |
| --- | --- |
| `compiles` | the CV rendered to a PDF |
| `page_fit` | `page_count` within the case's target (uses the *recorded* compile result, so no LaTeX toolchain needed) |
| `schema_complete` | name / email / summary / experience are present |
| `skills_anchored` | every listed skill is evidenced elsewhere in the CV |
| `quantified_bullets` | share of experience bullets containing a number |
| `no_duplicate_metrics` | the summary doesn't restate a bullet's metric |
| `must_have_coverage` | fraction of the job's human-authored must-haves evidenced |

Every evaluator returns a normalized `score ∈ [0,1]`, a `passed` gate, and specific
`findings` — the same findings become the runtime critic feedback in Phase 2.

### 2. LLM judge (`judge.py`) — paid, run nightly / on demand
A decomposed rubric (`grounding`, `job_fit`, `writing_impact`, `structure`), each
scored 1–4 with **reasoning before the score**, in a **separate context** from
generation (reduces self-grading bias). Also a **position-bias-controlled pairwise**
comparator (`pairwise()` runs both A/B orders and only declares a winner if they
agree) — the reliable way to measure the Phase 1 → Phase 2 delta.

> The judge must be validated against human labels before its numbers are trusted —
> score a handful of cases yourself and check agreement. The rubric here is shared
> with the Phase 2 critics by design: build it once, judge offline and critique online.

## The dataset (`dataset/cases.jsonl`)

Frozen, human-authored cases. Each carries the source material, the job description,
a page target, and the **must-haves** a good CV must visibly evidence (expressed as
OR-matched keyword groups, so coverage is measured with no model). Treat it like test
fixtures: version it, grow it deliberately, and don't tune prompts blindly against it.

## Running

```bash
# Hermetic evaluator tests — what CI runs on every push (no key, no network):
DATABASE_URL=postgresql+psycopg://x:x@localhost/x \
  uv run pytest app/tests/test_evals.py -v

# Full live eval (needs OPENAI_API_KEY and a LaTeX toolchain):
uv run python -m app.evals.runner --generator writer --out eval-report

# Deterministic-only live run (generates real CVs, skips the paid judge):
uv run python -m app.evals.runner --generator writer --no-judge --out eval-report

# Compare two saved runs; exits nonzero if any case regressed on any dimension:
uv run python -m app.evals.runner --compare baseline/report.json candidate/report.json
```

## CI (`.github/workflows/evals.yml`)

- **`deterministic`** — every push/PR. Hermetic, free, fast; gates the build.
- **`live`** — nightly + manual dispatch only. Installs LaTeX, regenerates CVs with the
  real model, runs the judge, and uploads `report.json` / `report.md` as an artifact.
  A paid, non-deterministic eval has no business blocking every push, so it is kept off
  the per-push path on purpose.

Set the `OPENAI_API_KEY` repository secret (and optionally an `EVAL_JUDGE_MODEL`
variable) to enable the live job.

## Phase 2 hook

Add a `LangGraphGenerator` (the generate → compile → parallel-critic → revise loop) to
`generators.py`, register it in `get_generator`, and:

```bash
uv run python -m app.evals.runner --generator writer    --out baseline
uv run python -m app.evals.runner --generator langgraph --out candidate
uv run python -m app.evals.runner --compare baseline/report.json candidate/report.json
```

`GeneratedCV.metadata` already carries fields for loop metrics (iterations,
convergence, latency) so the critic loop can be evaluated on process, not just output.
