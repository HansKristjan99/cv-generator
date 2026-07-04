# Backend refactor plan: LangGraph multi-agent CV pipeline

Status: **proposal** · Scope: `cv-generator-be` only · API contract with the FE stays unchanged.

This document describes how to replace the current linear generation pipeline
(`services/generation_pipeline.py` + hand-rolled tool loop in
`services/openai_client.py`) with a **LangGraph `StateGraph`** of specialized agents,
deterministic nodes, and explicit review loops. The goal is not "use LangGraph because
it's fashionable" — it is to make the pipeline produce *measurably better CVs* by
separating drafting from judging, and to make the orchestration observable, resumable,
and testable.

---

## 1. Goals & non-goals

### Goals

1. **Better CVs.** Introduce independent critics (hiring manager, readability/authenticity,
   fact-checker) that grade drafts against explicit rubrics, and a bounded
   revise-until-good loop. Today the writer reviews its own work inside one LLM call —
   self-review by the same context that produced the draft is the weakest form of review.
2. **Explicit orchestration.** Every step becomes a graph node with typed inputs/outputs.
   The ad-hoc `if gate_result is not None: ... else: ...` control flow becomes edges you
   can draw, log, and test.
3. **Durable, resumable runs.** Replace OpenAI server-side conversations as the source of
   truth with LangGraph checkpoints in our own Postgres. Human-in-the-loop (clarifying
   questions) becomes a first-class `interrupt()` instead of the fragile
   `conversation_id.startswith("pending-")` convention.
4. **Model-agnosticism.** Nodes call models through `init_chat_model` + structured
   output, so each node can be pinned to the cheapest model that does its job, and the
   provider can be swapped per node without touching orchestration.
5. **Testability.** Each node is a pure-ish function over state — unit-testable with a
   fake model, and the whole graph is integration-testable with an in-memory checkpointer.

### Non-goals

- No breaking FE changes. `/cv/generate/` request/response shapes, session polling,
  message `type` values (`cv`, `cover_letter`, `question`, `text`) all stay identical.
  (§5.1 adds one *additive* progress endpoint the FE can adopt on its own schedule.)
- No change to LaTeX rendering, templates, escaping, quotas, billing, auth.
- No streaming tokens to the FE (the FE polls; we only improve *what* it polls).
- Not a rewrite of the memory/invent/title agents' prompts — they get re-homed as nodes,
  prompts largely intact.

---

## 2. Current state (what we're replacing)

```
api/cv.py ── BackgroundTasks ──▶ run_pipeline()
                                   │
                                   ├─ RequirementsAgent (once per session, cached on CvSession)
                                   │    └─ deterministic gate: unmet must-haves → "question" message, STOP
                                   ├─ WriterAgent (one LLM call, compile_cv tool loop ≤10 iters,
                                   │    self-review inside the same prompt)
                                   ├─ render_cv (LaTeX → PDF)
                                   ├─ MemoryAgent (profile diff)
                                   └─ SessionTitleAgent
```

Pain points this refactor addresses:

| Problem | Where it lives today | LangGraph answer |
|---|---|---|
| Writer grades its own work | `writer.py` QUALITY REVIEW section of one mega-prompt | Independent critic nodes with their own contexts |
| Conversation state owned by OpenAI | `conversation_id` on `CvSession`, `OpenAIClient.init_conversation` | Postgres checkpointer, `thread_id = cv_session.id` |
| Ask-vs-write gate is stringly-typed | `pending-` prefix convention checked in `api/cv.py:187` | `interrupt()` + `Command(resume=...)` |
| Hand-rolled tool loop | `OpenAIClient.get_structured_output` (~80 lines of loop) | Graph edges; compile becomes a deterministic node |
| One mega-prompt does tailoring, dedup, skills policy, layout, page fit | `writer.py` SYSTEM_PROMPT (~130 lines) | Split across writer + per-critic rubrics; each prompt gets smaller and sharper |
| No visibility into *why* a CV came out weak | nothing | Per-node checkpoints, critique artifacts stored in state, optional LangSmith traces |

---

## 3. Guiding agentic principles

These are the rules the design below follows; they are worth stating because they
constrain every node spec:

1. **Single-writer principle.** Exactly one agent (the Writer) ever mutates the CV.
   Critics return *structured critiques*, never edited documents. This prevents
   ping-pong rewrites and keeps every change attributable.
2. **Drafting and judging need different contexts.** Critics see the *rendered artifact*
   (structured CV + PDF) and the *evidence*, not the writer's chain of thought or its
   system prompt. Fresh eyes catch what the author cannot.
3. **Deterministic where possible, LLM where necessary.** Compile, page-count check,
   keyword coverage, gate-question selection, loop accounting — all deterministic nodes.
   LLM calls are reserved for judgment (extract, write, critique).
4. **Bounded loops with a "best so far" fallback.** Every loop has a max iteration count,
   a score threshold to exit early, and keeps the best-scoring draft so a failed final
   revision can never make the output *worse* than an earlier draft.
5. **Critiques must be actionable diffs, not essays.** A critique is a list of
   `(severity, location, problem, suggested_fix)` items. The reviser applies the smallest
   edit that resolves them — the codebase already learned this lesson ("surgical edits,
   not regeneration" in `writer.py`); we keep it.
6. **Evidence-grounded generation.** Every claim in the CV must trace to a fact from the
   source material. We make this checkable by building an explicit **evidence ledger**
   (fact list with IDs) and having a fact-checker critic verify claims against it.
7. **Right-size the model per node.** Extraction/title/memory → small model; writing and
   hiring-manager critique → strong model. Cost is a product constraint (free tier);
   the graph makes per-node budgets explicit.
8. **Human-in-the-loop is a graph state, not an API hack.** Clarifying questions pause
   the graph via `interrupt()`; the user's answer resumes the same thread.

---

## 4. Target architecture

### 4.1 Dependencies

```toml
# pyproject.toml additions
"langgraph>=1.0",
"langgraph-checkpoint-postgres>=3.0",
"langchain>=1.0",            # init_chat_model, structured output
"langchain-openai>=1.0",     # current provider binding
```

`openai` stays (Stripe-style direct usage remains for file uploads if needed), but the
Responses-API conversation machinery is retired at the end of the migration.

### 4.2 Graph topology

One graph, two subgraph "lanes" (CV and cover letter) sharing intake and post-processing.
`thread_id` = `CvSession.id`; one graph invocation per user turn, with durable state
between turns carried by the checkpointer.

```mermaid
flowchart TD
    START([START]) --> intake[intake_router<br/><i>deterministic</i>]
    intake -->|kind == cover_letter| clwriter
    intake -->|first turn| par_extract
    intake -->|follow-up edit turn| writer

    subgraph par_extract [parallel fan-out — first turn only]
        req[requirements_extractor<br/><i>LLM · small</i>]
        ledger[evidence_ledger_builder<br/><i>LLM · small</i>]
    end
    par_extract --> gate{clarification_gate<br/><i>deterministic</i>}

    gate -->|unmet must-haves &<br/>ask budget left| ask[ask_user<br/><b>interrupt()</b>]
    ask -->|user answers /<br/>invented answers| ledger2[ledger_update<br/><i>LLM · small</i>] --> writer
    gate -->|covered or already asked| writer

    writer[writer<br/><i>LLM · strong</i><br/>draft or surgical edit] --> render[render<br/><i>deterministic:</i><br/>escape → LaTeX → PDF]
    render -->|compile error /<br/>overflow, retries left| writer
    render --> panel

    subgraph panel [review panel — parallel fan-out]
        hm[hiring_manager<br/><i>LLM · strong</i>]
        read[readability_reviewer<br/><i>LLM · small</i>]
        fact[fact_checker<br/><i>LLM · small</i>]
        ats[ats_keyword_check<br/><i>deterministic</i>]
    end
    panel --> verdict{critique_aggregator<br/><i>deterministic</i>}

    verdict -->|score ≥ threshold<br/>or budget exhausted| final[finalizer<br/><i>deterministic:</i> pick best draft]
    verdict -->|revise| writer

    clwriter[cover_letter_writer<br/><i>LLM · strong</i>] --> clrender[render_letter] --> clpanel[letter review panel<br/>hm + readability + fact] --> clverdict{aggregator}
    clverdict -->|revise| clwriter
    clverdict -->|done| final

    final --> post
    subgraph post [post-processing — parallel, non-blocking for quality]
        memory[memory_extractor<br/><i>LLM · small</i>]
        title[session_titler<br/><i>LLM · small</i>]
    end
    post --> persist[persist_message<br/><i>deterministic</i>] --> END([END])
```

Notes on the shape:

- **The compile loop moves out of the model and into the graph.** Today the writer calls
  a `compile_cv` tool up to 10 times inside one LLM call. Instead, `render` is a
  deterministic node; a conditional edge sends overflow/compile-failure back to the
  writer with a machine-generated instruction ("2.4 pages rendered, max 2 — cut the
  weakest content, here is the page-count per section estimate"). Rationale: every
  compile becomes a checkpointed, observable step; the strong model no longer burns
  context re-reading its own tool transcript; and it works identically across providers.
  The rendered PDF is attached (base64 content block) to the writer/critic messages so
  vision-capable review of layout is preserved.
- **Critics run in parallel** (LangGraph fan-out from `render` to the four panel nodes,
  fan-in at the aggregator). Wall-clock cost of the panel ≈ the slowest critic, not the sum.
- **The requirements extractor and evidence ledger run in parallel** on the first turn —
  they are independent reads of the same inputs.

### 4.3 State schema

One Pydantic/TypedDict state; reducers noted where lists append.

```python
class PipelineState(TypedDict):
    # ---- immutable per-session inputs (set on first turn) ----
    user_id: str
    cv_session_id: str
    kind: Literal["cv", "cover_letter"]        # per-turn, may flip on follow-ups
    job_description: str | None
    source_text: str | None
    source_file_ref: str | None                # temp path or stored PDF ref
    stored_profile: str                        # formatted user memory snapshot
    template_slug: str
    page_limit: int

    # ---- extraction artifacts (computed once, persisted via checkpoint) ----
    requirements: RequirementsAnalysis | None
    evidence: EvidenceLedger | None            # NEW — see below
    asked_gate_questions: bool                 # replaces the "pending-" convention

    # ---- per-turn working set ----
    user_message: str
    turn_mode: Literal["draft", "edit", "chat"]
    current_cv: CurriculumVitae | None         # canonical artifact being iterated
    current_letter: CoverLetter | None
    rendered: RenderResult | None              # latex, pdf bytes ref, page_count, success

    # ---- review loop bookkeeping ----
    critiques: Annotated[list[Critique], add]  # reducer: parallel critics append
    revision_round: int
    draft_history: list[ScoredDraft]           # (cv, rendered, aggregate_score) — for best-so-far
    compile_retries: int

    # ---- outputs ----
    final_message: dict | None                 # the asst_message persisted to Message
```

New schemas (in `app/schemas/`):

```python
class EvidenceFact(BaseModel):
    id: str                       # "F01", "F02", ...
    kind: Literal["job", "education", "project", "skill", "award", "metric", "note"]
    statement: str                # tightly paraphrased fact from source/profile/answers
    source: Literal["source_cv", "stored_profile", "user_answer", "attached_file"]

class EvidenceLedger(BaseModel):
    facts: list[EvidenceFact]

class CritiqueItem(BaseModel):
    severity: Literal["blocker", "major", "minor"]
    location: str                 # e.g. "experience[0].bullets[2]", "summary", "skills.Languages"
    problem: str
    suggested_fix: str            # concrete, minimal edit the writer can apply

class Critique(BaseModel):
    reviewer: Literal["hiring_manager", "readability", "fact_checker", "ats"]
    score: int                    # 1–10 against the reviewer's rubric
    verdict: Literal["approve", "revise"]
    items: list[CritiqueItem]
```

The **evidence ledger** is the load-bearing new idea. The requirements extractor already
judges "met/unmet with evidence"; the ledger generalizes that: every atomic fact the
candidate can truthfully claim gets an ID. The writer is instructed to build only from
ledger facts; the fact-checker verifies each CV claim maps to ≥1 fact. Gate answers and
invented experiences (`InventAgent`) are *appended to the ledger* with
`source="user_answer"`, which cleanly solves "how does new evidence flow into a rewrite"
— it's a ledger update, not a prompt-rebuilding hack.

### 4.4 Node specifications

Model tiers: **S** = small/cheap (today's `gpt-5.4-mini` class), **L** = strong writer
model (one tier up for the writer + hiring manager; configurable, may launch as S for
cost parity). All LLM nodes use `with_structured_output` and get `max_retries=2` with
schema-error feedback.

#### `intake_router` (deterministic)
Reads `kind`, whether a checkpoint exists, whether `current_cv` exists, and whether this
turn answers a pending interrupt. Emits `turn_mode`:
- `draft` — first CV of the session (or post-gate first write),
- `edit` — a `current_cv` exists; the writer must do surgical edits,
- `chat` — a small **S** classifier (or heuristic: no doc-affecting intent) routes pure
  conversation ("thanks!", "what does ATS mean?") to a cheap reply node that returns an
  `OtherMessage` without waking the panel. Today this variant-selection burden sits
  inside the writer's mega-prompt; hoisting it out keeps the writer single-purpose.

#### `requirements_extractor` (LLM · S) — port of `RequirementsAgent`
Same prompt and `RequirementsAnalysis` schema as today, minus the coverage judgment
against the candidate (that moves to a deterministic join against the ledger, see gate).
Runs once per session; result lives in checkpointed state (the
`CvSession.job_requirements` column becomes a read-model copy for the FE, or is dropped —
see §7).

#### `evidence_ledger_builder` (LLM · S) — NEW
Input: source CV text/file, stored profile. Output: `EvidenceLedger`. Prompt rules:
extract atomic, de-duplicated, tightly-paraphrased facts; never merge distinct metrics;
tag provenance. This is deliberately a *small-model extraction* job — no judgment.

#### `clarification_gate` (deterministic)
Joins `requirements × ledger`: a requirement is *met* if the extractor marked it met OR
a ledger fact covers it (the extractor already returns per-requirement evidence; keep
that, but re-validate must-haves against the ledger). If unmet must-haves exist AND
`not asked_gate_questions`: select top `REQUIREMENTS_MAX_GATE_QUESTIONS`, set
`asked_gate_questions=True`, and **`interrupt()`** with the questions payload. The
surrounding runner turns the interrupt into today's `type: "question"` message and sets
the session idle. The resume value (user's answer text, or `InventAgent` output when the
user clicks "invent answers") flows into `ledger_update`.

#### `ledger_update` (LLM · S)
Parses the user's free-text answers / invented answers into new `EvidenceFact`s and
appends them. Also re-flags which requirements they satisfy.

#### `writer` (LLM · L) — the only CV mutator
Two prompt modes sharing the `CV_GUIDE`:
- **draft**: inputs are the requirements checklist (met-first ordering), the evidence
  ledger (facts with IDs), page limit, template notes. Instructionally: *build only from
  ledger facts; annotate nothing; tailor ordering to the requirements; the panel will
  review, so do not self-review beyond the guide.* The mega-prompt sections about
  duplication/skills-vocabulary/quality-review shrink to guide-level guidance — the
  critics now enforce them with teeth.
- **edit**: inputs are `current_cv` + either the user's request (follow-up turn) or the
  aggregated `revision_plan` (loop turn) + overflow report when coming from `render`.
  Hard rule (kept verbatim from today): change only what the plan/request names; byte-
  identical elsewhere; never exceed the page limit to satisfy a critique.

Output: `CurriculumVitae` (or `OtherMessage` only in `chat` mode, which bypasses the panel).

#### `render` (deterministic)
`escape_cv_for_latex → cv_to_latex → compile_latex_to_pdf`. Emits `RenderResult`.
Conditional edge:
- compile failure → back to `writer` with the error tail (max `RENDER_MAX_RETRIES = 2`,
  then fail the run as today);
- `page_count > page_limit` → back to `writer` with a machine-built trim instruction
  (max `FIT_MAX_RETRIES = 3`; on exhaustion proceed to panel with an automatic
  `blocker` critique so the loop accounting stays in one place);
- else → fan out to the panel.

#### Review panel (parallel fan-out)

All critics receive: structured CV JSON, rendered PDF (as an attachment content block),
requirements checklist, evidence ledger. None receive the writer's prompt or history.
Each returns a `Critique`.

- **`hiring_manager` (LLM · L).** Persona: the hiring manager for *this* job description.
  Rubric: (a) would you shortlist this CV in a 30-second scan — what's above the fold;
  (b) requirement coverage — for each must-have, is it *evidenced* in a bullet, not
  name-dropped in skills; (c) seniority signal matches the role; (d) strongest material
  first; (e) anything that reads as filler. Must output a per-must-have coverage row
  (`requirement → where evidenced | missing`) — this coverage matrix is the plan's main
  quality instrument.
- **`readability_reviewer` (LLM · S).** The "reads human" agent. Rubric: buzzword and
  cliché density ("results-driven", "synergy", "leveraged" three times); uniform
  sentence rhythm and repeated verb openings across bullets; AI-tell phrasing; summary
  that characterizes rather than lists; bullet length discipline; jargon a human
  recruiter wouldn't say. Explicitly instructed to preserve facts — style-only fixes.
- **`fact_checker` (LLM · S).** For every claim (each bullet, summary sentence, skill
  item, metric): map to supporting `EvidenceFact` id(s). Anything unmapped is a
  `blocker` with fix "remove or soften to what F-nn supports". Inflated metrics
  (ledger says 20%, CV says 40%) are blockers. This is the anti-hallucination
  backstop, and it's cheap because it's pure lookup-style judgment.
- **`ats_keyword_check` (deterministic).** Case-insensitive term matching of
  requirement keywords/aliases against the CV text; flags must-have terms absent from
  the document, skills-section groups violating the normalized vocabulary (already a
  schema-adjacent rule — enforce in code, not prompt), duplicated facts (exact/fuzzy
  string dupes between summary and bullets). Free, instant, and catches the
  embarrassing misses.

#### `critique_aggregator` (deterministic)
- Aggregate score = weighted mean (hiring_manager 0.4, fact_checker 0.3, readability 0.2,
  ats 0.1). Any `blocker` ⇒ verdict `revise` regardless of score.
- Exit conditions (first that holds):
  1. no blockers AND aggregate ≥ `PANEL_SCORE_THRESHOLD` (start at 8.0) → **done**;
  2. `revision_round ≥ MAX_REVISION_ROUNDS` (start at 2) → **done, pick best draft**;
  3. score did not improve vs the previous round (non-convergence) → **done, best draft**;
  4. else → build `revision_plan` and loop to `writer`.
- `revision_plan` construction: merge all critique items, drop conflicts by priority
  (fact_checker > hiring_manager > readability > ats — truth beats fit beats style),
  cap at ~10 items per round so the edit stays surgical, carry dropped `minor` items to
  the next round only if one happens.
- Every scored draft is pushed to `draft_history`; the **finalizer** returns
  `max(draft_history, key=score)` — a revision can never regress the delivered CV.

#### `cover_letter_writer` + letter panel
Mirrors the CV lane with the existing `CoverLetterAgent` prompt as the writer,
`render_letter` deterministic, and a reduced panel (hiring_manager with a letter rubric,
readability — which matters *most* for letters, fact_checker). Same aggregator, same
loop budget. The letter lane reuses the session's requirements + ledger when present
(follow-up "now write a cover letter" turns get tailoring for free).

#### Post-processing (parallel, after `finalizer`)
- **`memory_extractor` (LLM · S)** — `MemoryAgent` as-is, but fed the *final* CV and the
  ledger diff (facts with `source="user_answer"` are the interesting new material).
  Failure is logged and swallowed, exactly like today.
- **`session_titler` (LLM · S)** — `SessionTitleAgent` as-is, first turn only.
- **`persist_message` (deterministic)** — builds the `asst_message` dict (`type: "cv"` /
  `"cover_letter"` / `"text"`), writes the `Message` row, flips session status to `idle`.
  Keeping persistence *inside* the graph as the terminal node means a crash between
  "CV done" and "message stored" is resumable from the checkpoint.

### 4.5 Loop control summary

| Loop | Trigger | Budget | Fallback |
|---|---|---|---|
| Compile-failure | LaTeX error | 2 | fail run (status `failed`, as today) |
| Page-fit | `page_count > limit` | 3 | proceed to panel with auto-blocker; aggregator picks best-fitting draft |
| Revision | blockers or score < 8.0 | 2 rounds | ship best-scoring draft from `draft_history` |
| Gate questions | unmet must-haves | once per session (`asked_gate_questions`) | write with unmet noted; hiring_manager judges accordingly |

Worst-case LLM calls per first turn ≈ 2 (extract) + 3 × (1 write + 3 critiques) = ~14
vs ~3–11 today (writer tool iterations hid the true count). With the S/L split and the
panel exiting early on approve, the *expected* case is ~7 calls, three of them small.
`PANEL_SCORE_THRESHOLD`, `MAX_REVISION_ROUNDS`, and per-node models all live in
`config.py` so cost can be tuned without code changes (and the free tier can run
`MAX_REVISION_ROUNDS=1`, paid tier 2 — a natural upsell lever).

### 4.6 Persistence, threads, and interrupts

- **Checkpointer:** `PostgresSaver` from `langgraph-checkpoint-postgres`, using the
  existing database. Its tables (`checkpoints`, `checkpoint_writes`, …) are created via
  an Alembic migration wrapping `checkpointer.setup()` (one-time DDL), so schema
  management stays in Alembic.
- **Thread mapping:** `thread_id = str(cv_session.id)`. Session deletion cascades to
  checkpoint rows (cleanup job or FK-less delete by thread_id in `sessions` service).
- **Turn lifecycle:**
  - New turn → `graph.invoke(input, config={"configurable": {"thread_id": ...}})` inside
    the background task (sync SQLAlchemy stack stays; LangGraph sync API).
  - Gate question → node calls `interrupt(questions_payload)`; invoke returns with
    `__interrupt__`; runner persists the `type:"question"` message, sets status `idle`.
  - User answers → `api/cv.py` detects the pending interrupt via
    `graph.get_state(config).next` (replaces the `pending-` prefix check) and resumes
    with `graph.invoke(Command(resume=answer_text), config)`.
  - Follow-up edit turn → plain `invoke` with the new `user_message`; `current_cv`,
    requirements, and ledger are already in the checkpointed state — **no more
    re-injecting the "CURRENT DOCUMENT" JSON into a prompt string in the API layer**
    (`api/cv.py:212-222` disappears).
- **Concurrency guard:** the existing `status in {pending, running} → 409` check stays;
  one in-flight invoke per thread.
- **Durability:** default (`"async"`) checkpoint durability; the terminal
  `persist_message` node makes end-of-run effects idempotent (upsert by
  `(cv_session_id, checkpoint_id)`).

### 4.7 Model access layer

`services/openai_client.py` is replaced by a thin `app/graph/llm.py`:

```python
def node_model(role: Literal["writer", "hiring_manager", "extractor", ...]) -> BaseChatModel:
    """init_chat_model(config.NODE_MODELS[role]) with retries and per-role max_tokens."""
```

- Structured output via `model.with_structured_output(Schema)` (provider-native JSON
  schema mode for OpenAI — same strictness as `responses.parse` today).
- PDF/file inputs become message content blocks (base64) instead of the Files API +
  server-side conversation attachments.
- `get_conversation_transcript` (used by `cv_invent.py`) is re-implemented from our own
  `Message` rows — better anyway, since it stops depending on OpenAI retention.

### 4.8 Observability & error handling

- **Tracing:** LangSmith via env vars (`LANGSMITH_TRACING=true`) — zero code, per-node
  latency/cost visibility. Optional but strongly recommended in staging.
- **Logging:** each node logs `session=<id> node=<name> round=<n>` on entry/exit; the
  aggregator logs the score vector every round — this is the "why was this CV weak"
  audit trail.
- **Failures:** node-level model errors retry twice with backoff (LangChain
  `max_retries`), then the run fails exactly as today (`status="failed"`, truncated
  error on the session). A failed run resumes from its last checkpoint if re-queued —
  a genuinely new capability (today a crash mid-writer loses everything).
- **Metrics to watch post-launch:** revision rounds per session (expect ≤1 median),
  panel approve-on-first-pass rate, fact_checker blocker rate (hallucination proxy),
  p95 turn latency, LLM $ per session.

---

## 5. API integration (no contract change)

`api/cv.py` keeps its validation/quota/session logic; the diff is confined to the tail:

| Today | After |
|---|---|
| builds `prompt_input` strings (`_full_context_prompt`, CURRENT DOCUMENT injection) | builds a typed `TurnInput` (message, new files, kind, template, page_count) |
| `background_tasks.add_task(run_pipeline, ...)` | `background_tasks.add_task(run_graph_turn, session_id, turn_input)` |
| `post_gate = conversation_id.startswith("pending-")` | `pending_interrupt = bool(graph.get_state(cfg).next)` |
| `run_pipeline` in `services/generation_pipeline.py` | `app/graph/runner.py::run_graph_turn` — invoke/resume, map interrupt → question message, map exceptions → failed status |

`api/cv_edit.py` (manual edits) writes the edited document back into graph state via
`graph.update_state(config, {"current_cv": ...})` so the next turn edits what the user
actually sees. `api/cv_invent.py` keeps calling `InventAgent`; its transcript source
switches to our `Message` rows (§4.7).

### 5.1 Live progress & explainable trace in the FE (additive)

The graph's node boundaries double as user-facing progress events. Today the FE shows a
static `CvGeneratingCard` spinner while polling every 2s; with the graph we can replace
it with a live step timeline — *"Reading the job description → Gathering proof →
Writing draft → Hiring manager reviewing → Revising (round 1) → Done"* — where each
step expands to show what the agent actually produced. The same data persists after the
run, so every assistant CV message can carry a "how this was made" trace: requirements
found, evidence gathered, panel scores per round, what each revision fixed. This is
both a UX win (generation takes minutes; a live narrative beats a spinner) and a
product differentiator (the review panel's work becomes *visible*, which also markets
the paid tier's extra revision rounds).

**Backend design (this repo's scope):**

- **`generation_events` table** (`session_id FK, turn int, seq int, node text,
  status text('started'|'done'|'error'), label text, payload JSONB, created_at`).
  Append-only; deleted with the session. Payloads are compact summaries, never PDFs.
- **Emission:** `runner.py` drives the graph with `graph.stream(..., stream_mode="updates")`
  instead of `invoke`. Each yielded node update maps through a per-node
  `summarize_for_event()` → one committed event row (own short DB transaction so the
  polling reader sees it immediately). Parallel panel critics emit independently as
  each finishes, which makes the fan-out visible in the UI for free.
- **Per-node payloads (expandable detail):**
  - `requirements_extractor` → the requirement list (the FE already renders this shape
    in `RequirementsBar`);
  - `evidence_ledger_builder` → fact count + the facts (kind, statement, source);
  - `clarification_gate` → questions asked / "all must-haves covered";
  - `writer` → mode (draft/edit/revision round n) + one-line change summary on edits;
  - `render` → page count vs limit, fit/overflow;
  - each critic → score, verdict, and its `CritiqueItem`s (severity, location, problem,
    fix) — this is the "see the replies" content, and it's all derived from the user's
    own data, so there is no leakage concern; internal prompts are never emitted;
  - `critique_aggregator` → aggregate score, decision (approve / revise round n / best-so-far);
  - `persist_message` → done.
- **API:** `GET /cv/sessions/{id}/progress?turn=latest` returning the ordered events;
  additive, so the existing FE keeps working untouched. The FE's existing 2s poll loop
  simply gains one call while status is `pending/running` — no SSE/WebSocket needed
  (revisit only if 2s granularity ever feels stale).
- **Tier gating (optional):** free tier sees step labels only; paid sees expanded
  critique payloads. Pure API-response filtering, decided at serialization time.

**FE sketch (separate PR, out of this plan's scope):** `CvGeneratingCard` becomes a
step list fed by the progress endpoint — collapsed rows with a spinner/check per step,
expandable to the payload; after completion the same component renders read-only from
the stored events under the assistant message.

Cost of the whole feature on the BE side: one table, one migration, ~10 small
summarizer functions, one endpoint — because the graph already produces every artifact
the timeline needs. This is the payoff of §3's "explicit orchestration" goal.

---

## 6. Code layout

```
app/
  graph/
    __init__.py
    state.py            # PipelineState, reducers, TurnInput
    llm.py              # node_model(), structured-output helpers, pdf content blocks
    builder.py          # build_graph() — nodes, edges, subgraphs, compile(checkpointer)
    runner.py           # run_graph_turn(): stream/resume, interrupt→message, error→status
    events.py           # per-node summarize_for_event() + generation_events writes (§5.1)
    checkpointer.py     # PostgresSaver wiring + lifecycle
    nodes/
      intake.py
      requirements.py   # ported from agents/requirements.py
      evidence.py       # ledger builder + ledger update
      gate.py           # deterministic gate + interrupt
      writer.py         # ported from agents/writer.py (prompt split draft/edit)
      render.py         # wraps services/latex + latex_escape
      cover_letter.py   # ported from agents/cover_letter.py
      critics/
        hiring_manager.py
        readability.py
        fact_checker.py
        ats.py          # deterministic
      aggregate.py      # scoring, revision_plan, finalizer
      post.py           # memory (wraps agents/memory), title, persist_message
  schemas/
    evidence.py         # EvidenceFact, EvidenceLedger
    critique.py         # Critique, CritiqueItem, ScoredDraft, RevisionPlan
```

`app/agents/` shrinks to `invent.py` + `memory.py` + `title.py` (called from nodes /
their own routes) and is eventually folded into `graph/nodes/`. `writer_guide.py` moves
next to the writer node.

---

## 7. Data model changes

One Alembic migration (`021_langgraph_checkpoints.py`):

1. Create LangGraph checkpoint tables (`PostgresSaver.setup()` DDL inlined).
2. `cv_sessions.conversation_id` → nullable, no longer written for new sessions
   (kept one release for rollback; dropped in a follow-up migration `022`).
3. `cv_sessions.job_requirements` — **keep as a read-model copy** written by the
   requirements node. Verified: the FE reads it (`LoadConversationResponse.job_requirements`
   → `RequirementsBar` in the chat header, and again in the job-application detail
   modal), so the column is load-bearing, not legacy.
4. `generation_events` table for the progress timeline (§5.1) — migration
   `022_generation_events.py` (the conversation_id drop shifts to `023`).
5. Session deletion: extend `services/sessions.py` delete path to purge checkpoint rows
   by `thread_id` and `generation_events` rows by session.

No changes to `users`, `messages`, memory tables, billing.

---

## 8. Migration plan

Phased so `main` stays shippable throughout; the legacy pipeline remains the default
until Phase 6.

**Phase 0 — scaffolding (no behavior change)**
- Add dependencies; pin versions; verify Python 3.14 compatibility of
  langgraph/langchain in CI.
- Migration 021 (checkpoint tables); `graph/checkpointer.py`; `graph/llm.py` with tests
  against a fake model.
- Config: `NODE_MODELS`, `PANEL_SCORE_THRESHOLD`, `MAX_REVISION_ROUNDS`,
  `FIT_MAX_RETRIES`, `RENDER_MAX_RETRIES`, `USE_LANGGRAPH_PIPELINE` flag (env, default
  false).

**Phase 1 — port the spine (parity, no panel)**
- `state.py`, `builder.py` with: intake → requirements → gate(interrupt) → writer →
  render(+fit loop) → persist. Writer prompt = today's prompt minus the compile-tool
  section (the loop is now graph edges).
- `runner.py` with invoke/resume and interrupt→question mapping.
- Wire `api/cv.py` behind `USE_LANGGRAPH_PIPELINE`.
- Exit criterion: with the flag on, existing manual test script produces a CV
  end-to-end, gate questions pause/resume, follow-up edits work, page limit enforced.

**Phase 2 — evidence ledger + fact_checker**
- `evidence.py`, ledger in state, writer prompt gains "build only from ledger facts".
- fact_checker critic + aggregator in blocker-only mode (no scores yet): any unmapped
  claim triggers one revision round.
- Exit criterion: seeded hallucination (a fake metric injected into a draft in tests)
  is caught and removed.

**Phase 3 — full review panel + revision loop**
- hiring_manager, readability, ats nodes; scoring, `revision_plan`, `draft_history`,
  best-so-far finalizer; loop budgets from config.
- Exit criterion: on a benchmark set (≈10 real JD + CV pairs, checked into
  `app/tests/fixtures/`), panel scores improve draft→final in ≥7/10 cases and never
  regress (best-so-far guarantees the latter by construction).

**Phase 4 — cover letter lane + post-processing**
- Cover-letter subgraph; memory/title as post nodes; `cv_edit.py` writes into graph
  state; `cv_invent.py` transcript from `Message` rows; invent answers resume the
  interrupt and append ledger facts.

**Phase 4b — progress timeline (§5.1)**
- Migration 022, `graph/events.py`, switch runner from `invoke` to `stream`,
  `GET /cv/sessions/{id}/progress`. BE ships dark (endpoint live, unused); the FE
  timeline component lands as its own PR whenever — no coupling to the cutover.

**Phase 5 — bake-off & tuning**
- Flag on in staging; A/B a sample of sessions (flag per user id hash) in prod.
- Compare: panel first-pass approve rate, latency, cost/session, and a blind
  side-by-side preference eval (same inputs through both pipelines, human pick).
- Tune threshold/rounds/models from data.

**Phase 6 — cutover & deletion**
- Default flag on → remove flag → delete `services/generation_pipeline.py`,
  `services/openai_client.py`, `agents/writer.py`, `agents/requirements.py`,
  `agents/cover_letter.py`, the `conversation_id` code paths, and migration 022 drops
  the column. Update `README.md` architecture section.

Each phase is one PR; the plan file gets updated with decisions/deviations as phases land.

---

## 9. Testing strategy

- **Node unit tests** (extend `app/tests/`): every LLM node tested with a
  `FakeChatModel` returning canned structured outputs; deterministic nodes tested
  directly (gate selection, aggregator exit conditions, ats matcher, revision-plan
  merging/priority, best-so-far selection).
- **Graph tests** with `InMemorySaver`: full-turn scenarios — first turn happy path;
  gate interrupt + resume; page overflow loop; compile failure; non-convergent panel
  (scores flat → exits with best draft); follow-up edit keeps untouched sections
  byte-identical (assert JSON equality outside the edited path).
- **Contract tests**: `asst_message` dicts match the existing FE-expected shapes for
  all four `type`s (snapshot tests).
- **Benchmark fixtures** (Phase 3): JD+CV pairs with expected properties asserted
  cheaply (must-have keyword presence, page count, no unmapped claims) rather than
  golden files.
- Existing `test_requirements.py`, `test_writer.py`, `test_latex.py`, `test_schemas.py`
  are ported, not deleted — they encode hard-won prompt/schema regressions.

---

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Cost blow-up from the panel | S-tier critics; parallel panel; early-exit threshold; `MAX_REVISION_ROUNDS` per tier; measure in Phase 5 before cutover |
| Latency regression (panel + rounds) | parallel fan-outs; expected case is 1 round; FE already treats generation as async/polled, so budget is minutes, not seconds |
| Critique ping-pong (readability vs hiring manager fighting) | single-writer + priority ordering in the aggregator + convergence exit + best-so-far |
| LangGraph/LangChain version churn | pin exact versions; graph API surface used is small (StateGraph, interrupt, PostgresSaver, Send) |
| Python 3.14 wheel availability | verify in Phase 0 CI before anything else lands |
| Checkpoint table growth | purge on session delete; retention job for sessions older than N days (align with existing session retention) |
| Structured-output drift vs `responses.parse` | Phase 0 tests lock schema round-trips per provider mode |
| The writer ignores the ledger | fact_checker blocker loop is the enforcement; prompt is the suggestion, the loop is the guarantee |

---

## 11. Deliberate design choices (and rejected alternatives)

- **Graph-level compile loop instead of the model-side `compile_cv` tool.** Rejected
  keeping the tool loop: it hides iterations from observability, couples us to
  provider-side conversation state, and burns strong-model context on tool transcripts.
  The PDF-as-attachment feedback the tool loop provided is preserved by attaching the
  render output to the next writer/critic call.
- **Critics return critiques, not edits.** Rejected "reflection pairs" where the critic
  rewrites the CV: two writers churn each other's prose, attribution is lost, and edit
  discipline ("byte-identical untouched sections") becomes unenforceable.
- **Deterministic aggregator instead of an LLM "judge of judges".** The exit decision is
  arithmetic over structured scores; an LLM adds cost and nondeterminism exactly where
  we want auditability. (Revisit only if critique-conflict resolution proves too crude.)
- **One graph with lanes instead of separate CV/letter graphs.** Shared intake, ledger,
  requirements, post-processing, and the session can switch document kinds mid-thread —
  matching today's per-turn `kind` behavior.
- **`interrupt()` for the gate instead of ending the run.** Ending and re-entering (like
  today) forces the API layer to reconstruct context; the interrupt keeps
  requirements + ledger warm in the checkpoint and makes "answers arrived" a resume,
  not a special first-turn rebuild.
- **Evidence ledger over free-text context.** Free text can't be *checked*; facts with
  IDs turn truthfulness from a prompt aspiration into a verifiable property.

---

## 12. Open questions

1. Which exact model for the L tier (writer + hiring manager)? Decide in Phase 5 with
   the bake-off data; config-only change.
2. Should the readability critic also see the *job description tone* (startup vs
   enterprise) to calibrate voice? Cheap to add to its prompt; try in Phase 3.
3. Free-tier loop budget: `MAX_REVISION_ROUNDS=1` vs 2 — cost data decides.
4. ~~Is `cv_sessions.job_requirements` read anywhere by the FE?~~ **Answered:** yes —
   `RequirementsBar` in the chat header and job-application detail modal. Column stays
   (§7.3).
5. Retention policy for checkpoint blobs (PDF bytes should live in `draft_history`
   as references, not raw bytes, if checkpoint size becomes an issue — measure).
6. Progress timeline tier gating (§5.1): show full critique payloads to everyone, or
   labels-only on free? Product call, zero code-structure impact — defer to launch.
