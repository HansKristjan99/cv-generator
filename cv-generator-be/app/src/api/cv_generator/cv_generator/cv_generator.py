import base64
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.src.core.cv_to_latex_converter.cv_to_latex_converter import cv_to_latex
from app.src.core.latex_compiler import compile_latex_to_pdf
from app.src.connections.openai_connection import OpenAIClient
from app.src.schemas.output_types.responses.cv.cv import CurriculumVitae
from app.src.schemas.output_types.responses.cv.cv_questions import QuestionsToImproveCv
from app.src.schemas.output_types.responses.cv.cv_writer_response import CVWriterResponse

router = APIRouter()

cb_guide = r"""# 2026 SWE CV Writing Guide (FAANG / Big Tech)

**Core thesis:** The strongest SWE CV is **plain, evidence-dense, technically specific, and role-tailored**. Bullets prove engineering impact with metrics, scope, and technical decisions, and give an interviewer obvious deep-dive hooks.

Length: 1 page for <8 yrs experience; 1–2 pages for senior/staff. Bullet-driven, impact-first, tailored per role.

---

## 1. What Big Tech screens for

**Technical fundamentals:** programming fluency in role languages; data structures & algorithms; testing/debugging/maintainability; software design; distributed systems, storage, networking for backend/infra; model deployment, evaluation, training/inference optimization for ML.

**Engineering impact categories** — quantify against these:

- **Performance:** latency (p50/p95/p99), throughput, CPU/memory, page load, cold-start.
- **Reliability:** availability, incidents, error rate, MTTR, SLOs, failed deploys, rollback rate.
- **Scale:** users, requests/day, events/day, data volume, services, regions, tenants.
- **Product:** conversion, activation, retention, adoption, support tickets.
- **Cost:** cloud spend, storage, compute, engineer hours.
- **Quality:** escaped defects, test coverage, flaky-test rate, security findings.
- **Developer productivity:** build time, CI runtime, deploy frequency, onboarding time.
- **Leadership:** mentoring, migrations, cross-team adoption, ownership scope.

**Judgment & ownership** (esp. senior): handling ambiguity, explicit tradeoffs, system-level (not ticket-level) improvements, owned production outcomes, influence without overclaiming team work.

---

## 2. Match the job description truthfully

Translate real experience into the employer's vocabulary — don't keyword-stuff. If the posting names "distributed systems, Kubernetes, Terraform, CI/CD, observability", surface those technologies inside concrete impact bullets, not just in a skills list.

Weak: `Worked on backend infrastructure.`
Strong: `Improved Kubernetes-based deployment reliability by adding Terraform-managed service config, CI/CD validation, and Prometheus alerts, reducing failed production deploys from 7/month to 2/month.`

---

## 3. Writing style

- **Bullet fragments, not prose.** Concise phrases starting with an action verb.
- **No pronouns.** `Built`, `Led`, `Migrated`, `Designed`, `Optimized`, `Debugged`, `Owned`, `Mentored` — never `I`, `we`, `my team`.
- **Direct engineering verbs:** designed, implemented, migrated, refactored, profiled, benchmarked, optimized, automated, instrumented, deployed, hardened, scaled, reduced, standardized. Avoid résumé theater (`spearheaded`, `revolutionized`, `leveraged`).
- **Cut filler:** `worked on`, `helped with`, `responsible for`, `assisted with`, `various`, `several`, `fast-paced`, `team player`, `passionate`, `detail-oriented`. Replace with evidence.
- **Length:** 1 line preferred, 2 if necessary, 3 only for exceptional staff-level work.
- **Front-load numbers.** Impact metric appears early, before the technical action.
- **Don't overclaim team outcomes.** Specify your part. Don't say `Built company-wide platform used by 400 engineers` when you owned one service inside it.
- **Technically specific but externally readable.** Use industry terms (Kafka, p95, idempotency), not internal product names (`Migrated FooBarService from Wombat v2 to BluePipe`).

---

## 4. Bullet formulas

**XYZ (default):** *Accomplished [X], measured by [Y], by doing [Z].* SWE variant: *Improved [metric] from [before] to [after] by [technical action].*
- `Reduced search p95 latency from 900ms to 310ms by adding query-result caching, denormalizing hot-path metadata, and moving ranking features to an async precompute job.`

**System built/migrated:** *Built/designed/migrated [system] using [approach], enabling [result] for [users/teams/business].*
- `Built Go-based event ingestion service with Kafka, PostgreSQL partitioning, and idempotent consumers, enabling 12 teams to process 350M events/day with <0.01% duplicate rate.`

**Reliability (infra/SRE/backend):** *Reduced [failure mode] by [measure] through [prevention/detection/mitigation].*
- `Lowered MTTR from 52 minutes to 18 minutes by adding trace correlation IDs, runbooks, and alert routing for 14 microservices.`

**Senior/staff leadership:** *Led/standardized [cross-team change], resulting in [outcome].*
- `Led 8-team migration from REST polling to Kafka event streams, cutting inventory-sync delay from 10 minutes to <30 seconds and eliminating 3 recurring incident classes.`

**Early-career project:** *Built [project] with [stack], implementing [nontrivial feature], measured by [users/benchmark/tests].*
- `Implemented LRU cache and trie-backed search suggestions in C++, improving benchmark lookup latency by 68% across 1M generated queries.`

---

## 5. Metrics vocabulary (use when business numbers are absent)

- **Performance:** p50/p95/p99 latency, RPS, throughput, query runtime, page load, CPU/memory, bundle size, cold-start, training time, inference cost.
- **Reliability:** error rate, incident count, MTTR, uptime, SLO compliance, failed deploys, rollback rate, data-loss events.
- **Scale:** DAU/MAU, requests/day, events/day, rows, TB processed, # services, # teams, # regions, # tenants.
- **Quality:** escaped defects, test coverage, flaky-test rate, vulnerabilities remediated, regression rate.
- **Developer productivity:** build time, CI runtime, deploy frequency, onboarding time, review cycle time, manual steps eliminated.
- **Product:** adoption, conversion, activation, retention, support-ticket reduction, funnel drop-off.

When exact numbers are confidential, use percentages, ranges, before/after, or relative improvements. Do not disclose confidential revenue, customer names, or unreleased products.

---

## 6. Section structure

- **Header:** name, city/country, email, phone, LinkedIn; GitHub/portfolio only if they reinforce the role. No photo, age, address, or "references on request".
- **Summary (optional):** one specific line — `Backend SWE with 4 years building Java/Kubernetes payment services; distributed systems, reliability, low-latency APIs`. Skip it for students. Never use `Passionate ... seeking a challenging opportunity`.
- **Skills:** grouped and truthful (Languages / Backend / Infrastructure / Testing). Strongest first. Don't list every tool ever touched. For seniors, skills support experience — they don't replace it.
- **Experience:** 3–5 bullets per recent role, 1–3 for older. Strongest bullet first. Past tense for past roles. Mention technologies in context, not as decoration. No generic duty bullets.
- **Projects:** matter most for interns, new grads, career switchers. Good projects are deployed, used, benchmarked, tested, or open source. Avoid tutorial clones and undeployed CRUD apps.
- **Education:** top of CV for new grads (degree, university, graduation, GPA if strong, relevant coursework, awards). Below experience and short for experienced engineers.
- **Open source / research / publications:** include only if role-relevant (maintainer status, accepted PRs in major projects, systems/ML/security research, relevant patents).

---

## 7. Candidate tier priorities

- **Intern / new grad** — prove coding ability, CS fundamentals, and ability to finish/deploy. Lead with education, then projects + internships. Three strong deployed projects beat eight shallow ones.
- **Mid-level** — prove ownership of a feature/service, production debugging, moderate-complexity design, shipping without heavy supervision. Quantify performance, reliability, and quality.
- **Senior / staff** — fewer, stronger bullets, each implying an interview deep-dive. Scope, ambiguity, architecture, cross-team influence, migrations, cost, technical strategy, mentoring, tradeoffs.
- **ML infra / AI systems** — model deployment, evaluation pipelines, data pipelines, training/inference optimization, GPU utilization, latency/cost tradeoffs, observability, reproducibility.
- **Frontend / full-stack** — product impact, performance, accessibility, design-system work, state management, testing, cross-functional delivery.

---

## 8. Before/after anchors

Backend — weak: `Worked on backend APIs for customer data.`
Strong: `Designed customer-profile API in Go with PostgreSQL indexes and Redis caching, reducing p95 lookup latency from 620ms to 180ms for 1.3M monthly users.`

Reliability — weak: `Monitored services and fixed production bugs.`
Strong: `Reduced payment-service SEV2 incidents from 5/quarter to 1/quarter by adding SLO dashboards, trace IDs, idempotency checks, and on-call runbooks.`

---

## 9. Remove

Objective statements; photos; age/gender/marital status/full address; "References available upon request"; skill bars; dense paragraphs; generic soft-skill claims (`passionate`, `team player`); internal acronyms without translation; tools you cannot explain; inflated or undefendable metrics; "Familiar with" lists that dilute stronger skills.
"""
# NOTE: "gpt-5.4-mini" looks like a typo (no such public model). Out of scope to change here.
_MODEL = "gpt-5.4"
SYSTEM_PROMPT = (
    "You are a senior technical recruiter and CV writer. "
    "Produce a modern, ATS-friendly, one-page CV from the SOURCE TEXT (and any attached file). "
    "Rules: lead every bullet with a strong action verb, quantify impact (%, $, count, time) wherever possible, "
    "use the Google X-Y-Z format ('Accomplished X, as measured by Y, by doing Z') for achievements, "
    "use 'MMM YYYY' dates, keep bullets to one line, and order each list most-relevant-first. "
    "Never invent facts not present in the source material.\n\n"
    "If a JOB DESCRIPTION is provided, tailor the CV toward that role: surface the most relevant experience, "
    "skills, and projects first, and prefer wording that mirrors the role's terminology (without fabricating). "
    "Then populate `job_requirements` with one entry per distinct requirement in the job description; "
    "for each, set `why_satisfied_by_cv` to the specific CV element that satisfies it (role, project, skill, "
    "education, etc.), or to the literal string 'Not satisfied' if no evidence exists in the source material.\n\n"
    "If no JOB DESCRIPTION is provided, return `job_requirements` as an empty list."
    "Here is a guide to writing good cvs, follow it as to the extend that you still have to output the particular shape right"
    "Never add bullets that are not relevant to the job description to sections, unless there is nothing else to add to a particular experience.\n\n"
    "COMPILATION:\n"
    "- A tool `compile_cv_to_pdf` is available. Call it with the candidate CurriculumVitae to verify the rendered page count.\n"
    "- First decide a target page count from the JOB DESCRIPTION:\n"
    "  * 1 page — junior, mid-level, most roles\n"
    "  * 2 pages — senior with 6+ years of relevant content\n"
    "  * 3 pages — only staff/principal with extensive publication, patent, or large-scope leadership history\n"
    "- Generate the CurriculumVitae, call the tool once, check page_count.\n"
    "- If page_count > target: tighten bullets, drop weakest entries, shorten the summary; call again.\n"
    "- If page_count < target: only expand if you have truthful evidence to add — never invent. Otherwise accept the shorter result.\n"
    "- HARD LIMIT: at most 3 compile calls total. After the third call, return whatever you have.\n"
    "- If the tool returns success=false, fix the indicated LaTeX/structural error and retry (counts toward the 3-call limit).\n"
     + cb_guide
)



class CvGeneratedResponse(BaseModel):
    latex: str
    pdf_base64: str

class CvQuestionResponse(BaseModel):
    questions: List[str]

class GenerateCVResponse(BaseModel):
    conversation_id: str
    content: CvGeneratedResponse | CvQuestionResponse


COMPILE_TOOL = {
    "type": "function",
    "name": "compile_cv_to_pdf",
    "description": (
        "Compile a candidate CurriculumVitae to PDF and return the rendered page count "
        "(plus any LaTeX error). Use to verify the CV fits the target page count before "
        "finalizing. You have a maximum of 3 calls."
    ),
    "parameters": CurriculumVitae.model_json_schema(),
}


def _handle_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name != "compile_cv_to_pdf":
        return {"success": False, "error": f"Unknown tool: {name}"}
    try:
        cv = CurriculumVitae(**args)
    except Exception as e:
        return {"success": False, "error": f"Invalid CV payload: {e}"}
    result = compile_latex_to_pdf(cv_to_latex(cv))
    return {
        "success": result.success,
        "page_count": result.page_count,
        "error": result.error[:600] if result.error else None,
    }


@router.post("/cv/generate/", response_model=GenerateCVResponse)
async def generate_cv(
    user_message: str | None = Form(None),
    text: str | None = Form(None),
    job_description: str | None = Form(None),
    file: UploadFile | None = File(None),
    conversation_id: str | None = Form(None),
) -> GenerateCVResponse:
    file_path: Path | None = None

    if conversation_id is None:
        if not (text or file) or not job_description:
            raise HTTPException(400, "Provide CV (text or file) and a job description on first turn.")
        if file is not None:
            with NamedTemporaryFile(delete=False, suffix=Path(file.filename or "").suffix) as tmp:
                tmp.write(await file.read())
                file_path = Path(tmp.name)
        prompt_input = (
            f"=== SOURCE TEXT ===\n{text or '(none provided)'}\n\n"
            f"=== JOB DESCRIPTION ===\n{job_description}\n\n"
            f"=== USER MESSAGE ===\n{user_message or 'Help me write a CV tailored to this job.'}"
        )
    else:
        if not user_message:
            raise HTTPException(400, "user_message is required on follow-up turns.")
        prompt_input = user_message

    response, conversation_id = OpenAIClient(_MODEL).get_structured_output(
        prompt_input,
        CVWriterResponse,
        system_prompt=SYSTEM_PROMPT,
        file=file_path,
        conversation_id=conversation_id,
        tools=[COMPILE_TOOL],
        tool_handler=_handle_tool,
    )

    if response is None:
        raise HTTPException(502, "Model returned no parsed output.")

    if isinstance(response.content, QuestionsToImproveCv):
        return GenerateCVResponse(
            conversation_id=conversation_id,
            content=CvQuestionResponse(questions=[q.question for q in response.content.questions]),
        )

    latex = cv_to_latex(response.content)
    final = compile_latex_to_pdf(latex)
    pdf_b64 = base64.b64encode(final.pdf_bytes).decode() if final.success and final.pdf_bytes else ""
    return GenerateCVResponse(
        conversation_id=conversation_id,
        content=CvGeneratedResponse(latex=latex, pdf_base64=pdf_b64),
    )
