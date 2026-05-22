"""The CV-writing style guide injected into the WriterAgent system prompt."""

CV_GUIDE = r"""# 2026 SWE CV Writing Guide (FAANG / Big Tech)

**Core thesis:** The strongest SWE CV is **plain, evidence-dense, technically specific, and role-tailored**. Bullets prove engineering impact with metrics, scope, and technical decisions, giving an interviewer obvious deep-dive hooks. The required page count is set by the user each run — fill it well; do not decide the length yourself.

---

## 1. What Big Tech screens for

**Technical fundamentals:** programming fluency in role languages; data structures & algorithms; testing/debugging/maintainability; software design; distributed systems, storage, networking for backend/infra; model deployment, evaluation, training/inference optimization for ML.

**Engineering impact categories** — quantify against these; this is also your metrics vocabulary when business numbers are absent:

- **Performance:** latency (p50/p95/p99), throughput/RPS, query runtime, page load, CPU/memory, bundle size, cold-start, training/inference time and cost.
- **Reliability:** availability/uptime, incidents, error rate, MTTR, SLO compliance, failed deploys, rollback rate, data-loss events.
- **Scale:** users (DAU/MAU), requests/day, events/day, data volume (rows, TB), services, regions, tenants.
- **Product:** conversion, activation, retention, adoption, support-ticket reduction, funnel drop-off.
- **Cost:** cloud spend, storage, compute, engineer hours.
- **Quality:** escaped defects, test coverage, flaky-test rate, vulnerabilities remediated, regression rate, security findings.
- **Developer productivity:** build time, CI runtime, deploy frequency, onboarding time, review cycle time, manual steps eliminated.
- **Leadership:** mentoring, migrations, cross-team adoption, ownership scope.

When exact numbers are confidential or absent, use percentages, ranges, before/after, or relative improvements. Never disclose confidential revenue, customer names, or unreleased products.

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
- **Length:** keep bullets short — the shorter the better. One line is ideal; allow two, or three at most, only when the substance genuinely needs the space. Never pad to fill lines.
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

## 5. Section structure

- **Header:** name, city/country, email, phone, LinkedIn; GitHub/portfolio only if they reinforce the role. No photo, age, address, or "references on request".
- **Summary:** one to a few specific lines — `Backend SWE with 4 years building Java/Kubernetes payment services; distributed systems, reliability, low-latency APIs`. Keep it short for juniors. Never use `Passionate ... seeking a challenging opportunity`.
- **Skills:** grouped and truthful (Languages / Backend / Infrastructure / Testing). Strongest first. Don't list every tool ever touched. For seniors, skills support experience — they don't replace it.
- **Experience:** 3–5 bullets per recent role, 1–3 for older. Strongest bullet first. Past tense for past roles. Mention technologies in context, not as decoration. No generic duty bullets.
- **Projects:** matter most for interns, new grads, career switchers. Good projects are deployed, used, benchmarked, tested, or open source. Avoid tutorial clones and undeployed CRUD apps.
- **Education:** top of CV for new grads (degree, university, graduation, GPA if strong, relevant coursework, awards). Below experience and short for experienced engineers.
- **Open source / research / publications:** include only if role-relevant (maintainer status, accepted PRs in major projects, systems/ML/security research, relevant patents).

---

## 6. Candidate tier priorities

- **Intern / new grad** — prove coding ability, CS fundamentals, and ability to finish/deploy. Lead with education, then projects + internships. Three strong deployed projects beat eight shallow ones.
- **Mid-level** — prove ownership of a feature/service, production debugging, moderate-complexity design, shipping without heavy supervision. Quantify performance, reliability, and quality.
- **Senior / staff** — fewer, stronger bullets, each implying an interview deep-dive. Scope, ambiguity, architecture, cross-team influence, migrations, cost, technical strategy, mentoring, tradeoffs.
- **ML infra / AI systems** — model deployment, evaluation pipelines, data pipelines, training/inference optimization, GPU utilization, latency/cost tradeoffs, observability, reproducibility.
- **Frontend / full-stack** — product impact, performance, accessibility, design-system work, state management, testing, cross-functional delivery.

---

## 7. Before/after anchors

Backend — weak: `Worked on backend APIs for customer data.`
Strong: `Designed customer-profile API in Go with PostgreSQL indexes and Redis caching, reducing p95 lookup latency from 620ms to 180ms for 1.3M monthly users.`

Reliability — weak: `Monitored services and fixed production bugs.`
Strong: `Reduced payment-service SEV2 incidents from 5/quarter to 1/quarter by adding SLO dashboards, trace IDs, idempotency checks, and on-call runbooks.`

---

## 8. Remove

Objective statements; photos; age/gender/marital status/full address; "References available upon request"; skill bars; dense paragraphs; generic soft-skill claims (`passionate`, `team player`); internal acronyms without translation; tools you cannot explain; inflated or undefendable metrics; "Familiar with" lists that dilute stronger skills.
"""
