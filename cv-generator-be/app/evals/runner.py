"""Eval runner + reporter + CLI.

Runs a generator over the frozen dataset, applies the deterministic evaluators and
(unless disabled) the LLM judge, and writes a machine-readable ``report.json`` plus a
human ``report.md``. Also compares two saved runs and flags **per-case regressions** —
because a change that lifts the average while quietly breaking three cases is usually
a bad change.

Usage::

    uv run python -m app.evals.runner --generator writer --out eval-report
    uv run python -m app.evals.runner --generator writer --no-judge --out eval-report
    uv run python -m app.evals.runner --compare baseline.json candidate.json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

from app.evals.dataset import load_cases
from app.evals.deterministic import run_deterministic
from app.evals.types import CaseReport, EvalRun


def run(generator_name: str, *, use_judge: bool = True) -> EvalRun:
    """Generate + score every case. Imports of generator/judge are deferred so the
    deterministic test path never pulls in ``openai``."""
    from app.evals.generators import get_generator

    generator = get_generator(generator_name)
    cases = load_cases()
    run_result = EvalRun(
        generator=generator.name,
        created_at=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    )

    judge_cv = None
    if use_judge:
        from app.evals.judge import judge_cv as _judge_cv

        judge_cv = _judge_cv

    for case in cases:
        print(f"  · generating: {case.id}", file=sys.stderr)
        gen = generator.generate(case)
        results = run_deterministic(case, gen)
        if judge_cv is not None:
            results += judge_cv(case, gen)
        run_result.cases.append(CaseReport(case_id=case.id, results=results))

    return run_result


def render_markdown(run_result: EvalRun) -> str:
    means = run_result.dimension_means()
    pass_rates = run_result.dimension_pass_rates()
    lines = [
        f"# CV Eval Report — `{run_result.generator}`",
        f"_generated {run_result.created_at}_",
        "",
        f"**Cases:** {len(run_result.cases)} · "
        f"**Fully-passing cases:** {sum(c.passed for c in run_result.cases)}/{len(run_result.cases)}",
        "",
        "## Scores by dimension",
        "",
        "| Dimension | Mean score | Pass rate |",
        "| --- | ---: | ---: |",
    ]
    for dim in means:
        lines.append(f"| {dim} | {means[dim]:.2f} | {pass_rates[dim]*100:.0f}% |")

    lines += ["", "## Per-case results", ""]
    for case in run_result.cases:
        status = "✅" if case.passed else "❌"
        lines.append(f"### {status} `{case.case_id}`")
        lines.append("")
        lines.append("| Dimension | Score | Pass | Detail |")
        lines.append("| --- | ---: | :---: | --- |")
        for r in case.results:
            mark = "✅" if r.passed else "❌"
            detail = r.detail.replace("\n", " ")[:120]
            lines.append(f"| {r.dimension} | {r.score:.2f} | {mark} | {detail} |")
        findings = [f for r in case.results for f in r.findings]
        if findings:
            lines.append("")
            lines.append("<details><summary>findings</summary>")
            lines.append("")
            lines += [f"- {f}" for f in findings]
            lines.append("")
            lines.append("</details>")
        lines.append("")
    return "\n".join(lines)


def write_report(run_result: EvalRun, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(run_result.model_dump_json(indent=2))
    (out_dir / "report.md").write_text(render_markdown(run_result))
    print(f"wrote {out_dir/'report.json'} and {out_dir/'report.md'}", file=sys.stderr)


def compare(baseline_path: Path, candidate_path: Path) -> int:
    """Diff two runs per-case-per-dimension. Returns nonzero if any case regressed."""
    base = EvalRun.model_validate_json(baseline_path.read_text())
    cand = EvalRun.model_validate_json(candidate_path.read_text())
    base_scores = {
        (c.case_id, r.dimension): r.score for c in base.cases for r in c.results
    }

    regressions: list[str] = []
    improvements: list[str] = []
    for c in cand.cases:
        for r in c.results:
            prev = base_scores.get((c.case_id, r.dimension))
            if prev is None:
                continue
            delta = round(r.score - prev, 3)
            if delta < -1e-9:
                regressions.append(f"{c.case_id}/{r.dimension}: {prev:.2f} → {r.score:.2f} ({delta:+.2f})")
            elif delta > 1e-9:
                improvements.append(f"{c.case_id}/{r.dimension}: {prev:.2f} → {r.score:.2f} ({delta:+.2f})")

    print(f"\n{base.generator} → {cand.generator}")
    print(f"  improvements: {len(improvements)}")
    for line in improvements:
        print(f"    + {line}")
    print(f"  regressions: {len(regressions)}")
    for line in regressions:
        print(f"    - {line}")
    if regressions:
        print("\nREGRESSIONS DETECTED — candidate made at least one case worse.")
        return 1
    print("\nNo per-case regressions.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or compare CV evals.")
    parser.add_argument("--generator", default="writer", help="generator name to run")
    parser.add_argument("--no-judge", action="store_true", help="skip the (paid) LLM judge")
    parser.add_argument("--out", default="eval-report", help="output directory for the report")
    parser.add_argument(
        "--compare", nargs=2, metavar=("BASELINE", "CANDIDATE"),
        help="compare two report.json files and flag regressions",
    )
    args = parser.parse_args(argv)

    if args.compare:
        return compare(Path(args.compare[0]), Path(args.compare[1]))

    run_result = run(args.generator, use_judge=not args.no_judge)
    write_report(run_result, Path(args.out))
    # Exit nonzero if any deterministic gate failed, so live CI surfaces hard breakages.
    hard_fail = any(
        not r.passed for c in run_result.cases for r in c.results if r.kind == "deterministic"
    )
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
