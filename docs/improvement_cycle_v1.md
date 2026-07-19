# Prompt Improvement Cycle — Iterations 1–3

**Iteration 1 date:** 2026-05-16 — prompt-only changes (plan_generator@1.1.0, solution_architect@1.2.0, schedule_estimator prompt strengthened)
**Iteration 2 date:** 2026-07-17 — root-cause fix: `schedule_estimator` context assembly (see §7); iteration 1's prompt-only change measured **no improvement** (§6)
**Iteration 3 date:** 2026-07-17 — `solution_architect` still 0.20 after v1.2.0; found a real differentiation gap (options A/C shared a critical-path design) AND a judge-rubric bug (judge penalized a defensible problem_type against a category that doesn't exist in the taxonomy) — see §9
**Baseline experiment:** `golden-brd-llm-judge` (prompt versions: all agents @ 1.0.0)
**Status:** iteration 2 and 3 fixes applied, not yet re-scored — next step is `run_golden_brds` + `run_experiments` + `compare_experiments.py --latest --explanations`

---

## 1. Lesson: How the improvement cycle works

```
1. venv/bin/python -m evals.run_golden_brds      # re-run 4 BRDs → new traces + dataset examples
2. venv/bin/python -m evals.run_experiments       # LLM-as-judge scores new outputs
3. Phoenix UI → Datasets & Experiments → golden_brd_evals → Experiments tab
   → click the new experiment row → compare llm_quality scores per agent × BRD
4. Identify low-scoring rows → expand the llm_quality cell → read the judge explanation
5. Map the explanation to a specific failure mode → edit the prompt in prompts/registry.py
   (or inline in the agent file for schedule_estimator) → bump the version
6. Repeat from step 1
```

Getting the git diff of prompt changes before running:
```bash
git diff prompts/registry.py agents/planning/schedule_estimator.py
```

---

## 2. Baseline scores (v1.0.0 — before changes)

Scores read from Phoenix UI `golden-brd-llm-judge` experiment, `llm_quality` column.
`output_completeness` was 1.00 for all agents (all fields populated).

| Agent | BRD | llm_quality | Judge explanation |
|---|---|---|---|
| plan_generator | brd_adverse_action_reason_codes | 0.20 | Includes out-of-scope items (Jira controls, FR-08); phase mapping incomplete; truncates BRD requirements |
| solution_architect | brd_adverse_action_reason_codes | 0.20 | Options not genuinely different architecturally; components use generic/invented names instead of RAG-grounded Arbor services |
| solution_architect | brd_application_fraud_scoring | 0.20 | Problem type reasonable but options not genuinely different; components include "Python 3.12 scoring worker service", "Amazon RDS PostgreSQL" — non-RAG generic names |
| solution_architect | brd_first_party_fraud_case_management | 0.20 | Options plausible but not genuinely different; components mostly generic or duplicated instead of named from RAG context |
| schedule_estimator | brd_adverse_action_reason_codes | 0.20 | Risks implied rather than explicitly mitigated; assumptions not tied to BRD specifics (3-engineer team, ScoreIQ/Aurora services, Q3 2025 deadline) |

---

## 3. Root cause analysis

### solution_architect — pattern across all 4 BRDs

**Failure mode 1: Generic component names**  
The model produced components like:
- `"Python 3.12 scoring worker service"` → should be `"FastAPI scoring service on EKS"`  
- `"Amazon RDS PostgreSQL"` → should be `"Aurora PostgreSQL"` (Arbor's specific variant)  
- `"message queue"` → should be `"Amazon SQS"`  

**Why it happened:** The design_system prompt said "ground every component in the company's known stack" but only referenced it as "see context below" (the RAG chunks). The model had no explicit enumeration of what names to use or prohibition on generic names.

**Failure mode 2: Options not genuinely different**  
Options A, B, C would share the same processing model (all synchronous or all async) with only configuration differences — e.g., different queue depths or worker counts.

**Why it happened:** The prompt listed "meaningful axes of difference" but did not require the options to differ on those axes, nor explain what "not meaningfully different" looks like concretely.

---

### plan_generator — brd_adverse_action_reason_codes

**Failure mode: Out-of-scope items in phases**  
The plan included deliverables touching Jira-linked approval workflows (FR-08) and compliance controls that the BRD's out-of-scope section explicitly deferred.

**Why it happened:** The original rule was one line: "Respect out-of-scope items — do not create phases for excluded work." Too brief. The model did not reliably read the out-of-scope section before generating phases.

**Failure mode 2: Missing BRD requirements in phases**  
Some functional requirements from the BRD had no corresponding phase deliverable.

**Why it happened:** No explicit traceability check was enforced — the model was not prompted to verify each requirement was covered before finalising.

---

### schedule_estimator — brd_adverse_action_reason_codes

**Failure mode 1: Vague assumptions**  
Assumptions like "team will be fully available" with no reference to the specific team size stated in the BRD (3 engineers) or named services.

**Failure mode 2: Risks without concrete mitigations**  
Risks named the problem but mitigation was "monitor" or implied — no concrete action tied to a specific phase or service.

**Why it happened:** The prompt gave one good example per field but no explicit REQUIREMENT that tied each assumption/risk to BRD-specific details. The model defaulted to generic language when specific details weren't demanded.

---

## 4. Prompt changes made (v1.0.0 → v1.1.0)

### 4a. solution_architect `design_system` — prompts/registry.py (v1.2.0)

**v1.2.0 fix — NAMING RULE (verbatim from context):**
```
NAMING RULE: Use service names exactly as they appear in the company context above — do not
paraphrase, generalise, or invent variants. Copy the name verbatim from the context.
  Wrong → Right (examples of the required transformation):
  "message queue"  → use the specific queue service named in the context (e.g. "Amazon SQS")
  "database"       → use the specific store named in the context (e.g. "Aurora PostgreSQL")
  "cache"          → use the specific cache named in the context (e.g. "Redis")
  "Python worker"  → use the BRD-specific service name (e.g. "ScoreIQ scoring service")
If a component is not named in the context, use the BRD's own name for it.
Generic labels ("backend", "worker service", "data store", "API gateway") are never acceptable.
```

**Added: DIFFERENTIATION RULE (structural axes)**
```
DIFFERENTIATION RULE: Options A, B, and C must differ on at least one of these structural axes:
  - processing model: synchronous in-request vs. asynchronous queue-backed vs. streaming
  - deployment unit: in-process module within an existing service vs. standalone microservice
  - data pattern: read-through cache vs. materialised snapshot vs. event-sourced ledger
  - operational model: fully managed cloud service vs. self-hosted on container platform
A different configuration or tuning of the same approach does NOT count as a different option.
```

---

### 4b. plan_generator `system` — prompts/registry.py

**Added: TRACEABILITY CHECK**
```
TRACEABILITY CHECK — before finalising phases, verify for each functional requirement in the BRD:
  → Does at least one phase deliverable explicitly address it?
  If a requirement is uncovered, add a deliverable to the appropriate phase.
  Do not omit or truncate requirements from the BRD.
```

**Strengthened: SCOPE ENFORCEMENT (single line → explicit checklist)**
```
SCOPE ENFORCEMENT — the BRD's out-of-scope section is a hard boundary:
  → Read the out-of-scope section first and keep a mental checklist.
  → Do NOT create any phase, objective, or deliverable that touches an out-of-scope item.
  → If you are unsure whether something is in scope, assume it is out-of-scope and omit it.
  Items that commonly slip in: third-party integrations the BRD explicitly excludes, admin tooling
  listed as out-of-scope, specific regulatory controls (e.g. FR-08, Jira-linked approvals) the
  BRD defers to a later release.
```

---

### 4c. schedule_estimator `_SCHEDULE_SYSTEM` — agents/planning/schedule_estimator.py

**Added: REQUIREMENT tag on assumptions (must name specific BRD details)**
```
REQUIREMENT: every assumption MUST name at least one specific detail from the BRD or plan —
  the exact engineer count and roles, a named service (e.g. "Aurora PostgreSQL", "ScoreIQ API"),
  a specific BRD constraint, or the stated delivery deadline (e.g. "Q3 2025 production target").
```

**Added: REQUIREMENT tag on risks (must name phase/service + concrete mitigation)**
```
REQUIREMENT: every risk MUST (a) name the specific phase, service, or BRD constraint it relates to,
  AND (b) state a concrete mitigation action — not "monitor", "escalate", or "plan accordingly".
```

**Added: additional Bad examples** to anchor the model away from vague language.

**Added: closing rule** — "Every assumption and risk must be traceable to a specific element in the BRD or plan inputs"

---

## 5. How to capture after-scores

```bash
# Terminal 1 (if Phoenix not already running):
venv/bin/python -m phoenix.server.main serve

# Terminal 2:
venv/bin/python -m evals.run_golden_brds      # re-runs pipeline with new prompts
venv/bin/python -m evals.run_experiments       # LLM-as-judge on new outputs; saves a JSON snapshot to evals/results/
```

**Comparing runs — terminal-first, no screenshots needed:**

```bash
venv/bin/python -m evals.compare_experiments --latest                # score table, all evaluators incl. llm_quality
venv/bin/python -m evals.compare_experiments --latest --explanations # + judge reasoning per example
```

`run_experiments.py` now pulls the `llm_quality` score *and* the judge's explanation out of the
`RanExperiment` result and writes them into the snapshot JSON (`evals/results/experiment_<ts>.json`)
under an `examples` array — one row per agent × BRD × evaluator, with `score`, `label`, and
`explanation`. Previously only the rule-based `critic_score`/`output_completeness` were saved
locally, and `llm_quality` could only be read from the Phoenix UI. (In the process of wiring this
up we also found `_compute_local_scores` was reading `example.input` via `getattr` on a plain
dict, which silently returned `{}` every time — every past snapshot's `scores` block was a single
bogus `"unknown"` bucket. Fixed by switching to dict access.)

Screenshots of the Phoenix UI are still useful for the portfolio article (visual before/after), but
the JSON snapshots + `compare_experiments.py --explanations` are now the fast local feedback loop —
use them while iterating, save a screenshot only for the write-up.

---

## 6. After scores — Iteration 1 (v1.1.0, prompt-only changes)

| Agent | BRD | llm_quality (before) | llm_quality (after) | Delta |
|---|---|---|---|---|
| schedule_estimator | brd_adverse_action_reason_codes | 0.20 | 0.20 | **0.00 — no change** |
| plan_generator | brd_adverse_action_reason_codes | 0.20 | — | not yet re-compared |
| solution_architect | brd_adverse_action_reason_codes | 0.20 | — | not yet re-compared |
| solution_architect | brd_application_fraud_scoring | 0.20 | — | not yet re-compared |
| solution_architect | brd_first_party_fraud_case_management | 0.20 | — | not yet re-compared |

**Confirmed result for `schedule_estimator`:** re-running `run_golden_brds` + `run_experiments`
after the v1.1.0 prompt changes (REQUIREMENT tags, concrete Good/Bad examples) produced the exact
same `llm_quality` score (0.20) and the same judge complaint as the baseline — assumptions still
not tied to the 3-engineer team, ScoreIQ/Aurora, or the Q3 2025 deadline. **The prompt-only fix had
zero measurable effect.** See Iteration 2 below for the root cause.

_Remaining rows (plan_generator, solution_architect) pending a `compare_experiments.py --latest`
run to confirm before recording numbers — do not assume they improved just because the prompt
changed._

---

## 7. Iteration 2 — root cause was context assembly, not prompt wording

Tightening the `schedule_estimator` prompt (v1.1.0) did not move the score at all. Before writing
another prompt tweak, we checked what the model actually *received*, not just what it was *told*.

**Finding:** `_format_brd()` in `agents/planning/schedule_estimator.py` only forwarded 3 of the
BRD's 12 possible section types to the model (`objective`, `constraints`, `timeline`). Checking the
real classifier output for `brd_adverse_action_reason_codes.md` confirmed the facts the judge
wanted were in sections that were being silently dropped:

| Judge wants | Actual section (classified type) | Forwarded to the model? |
|---|---|---|
| Named "3-engineer team" | Doesn't exist in this BRD at all — only in `team_skills.md`, a separate RAG doc `schedule_estimator` never queries | ❌ never available |
| "ScoreIQ" | Scope / Functional Requirements (`functional_requirements`) | ❌ dropped |
| "Q3 2025" deadline | Problem Statement (`background`) | ❌ dropped |
| "Aurora PostgreSQL" | Constraints (`constraints`) | ✅ this one got through |

No amount of REQUIREMENT-tag rewriting can make a model cite a fact it was never shown. That's the
whole explanation for the flat 0.20 → 0.20 result above.

**Fix applied (`agents/planning/schedule_estimator.py`):**
1. `_format_brd()` now includes `background`, `functional_requirements`, and `stakeholders` in
   addition to the original three — surfaces ScoreIQ, the Q3 2025 deadline, and stakeholder roles.
2. The prompt's "Good" assumption example no longer asserts a specific headcount
   (`"3-engineer team (1 backend/data, 1 full-stack, 1 QA)"`) that happened to match this BRD's
   expected judge answer verbatim — that's teaching to the eval, not teaching a pattern. Replaced
   with different illustrative numbers plus an explicit instruction: derive headcount from
   stakeholder roles + tech stack effort when the BRD doesn't state it, and say so as a derived
   estimate rather than presenting an invented number as BRD fact.

**Status:** fix applied, not yet re-scored. Next step: `run_golden_brds` + `run_experiments`, then
`compare_experiments.py --latest --explanations` to confirm `llm_quality` actually moves this time.

---

## 9. Iteration 3 — `solution_architect` still 0.20 on `brd_adverse_action_reason_codes`: one real bug, one rubric bug

While building the `--explanations` comparison flow we also caught that the JSON extraction itself
was silently dropping every judge explanation (`result.get("explanation")` was always `None` — our
evaluators return a 2-tuple `(score, text)`, and Phoenix's experiment runner maps a bare 2-tuple to
`(score, label)`, not `(score, explanation)`. Fixed in `run_experiments.py` by falling back to
`label` when `explanation` is empty). Once the real judge text was visible, two distinct complaints
came through for `solution_architect` on `brd_adverse_action_reason_codes`:

**9a. Differentiation complaint — real bug.** Pulled the full agent output directly from the
Phoenix dataset (not just the score) to check it against the judge's claim. Option A ("Inline
ScoreIQ reason-code module") and Option C ("Hybrid synchronous lookup with async audit snapshot")
turned out to share an almost identical scoring-path design — both are an in-process, synchronous
resolver embedded in the scoring worker, reading the same Aurora catalogue. The *only* difference is
what happens on the catalogue-**promotion** side (A promotes synchronously, C promotes via a
background worker) — confirmed by the agent's own recommendation text: *"Compared with Option C, it
avoids background promotion workflow complexity... while still delivering immutable approved codes,
versioned snapshots, and full auditability."* Only Option B (standalone microservice) was genuinely
distinct. Root cause: the v1.2.0 DIFFERENTIATION RULE only required the option *set* to diverge on
one axis somewhere — it didn't require divergence on the axis that governs the actual
latency-critical request path, so two options could look different in prose while sharing the same
critical-path architecture with a different optional side-workflow bolted on.
**Fix:** added a CRITICAL PATH RULE to `design_system` (`solution_architect` → v1.3.0) — when a hard
latency/SLA constraint forces the same processing model everywhere, options must diverge on at least
two of the *remaining* axes so the critical-path design itself differs, not just an admin workflow.

**9b. problem_type complaint — rubric bug, not an agent bug.** The judge flagged `enhancement` as
"misclassified... despite being a compliance-driven regulatory remediation." But
`solution_architect`'s `classify_system` prompt only offers 6 fixed categories
(`greenfield`/`new_feature`/`migration`/`integration`/`poc`/`enhancement`) — **there is no
compliance/regulatory category** for the agent to pick. The judge was holding the agent to a
category outside the system it was grading, because `_AGENT_RUBRIC["solution_architect"]` in
`run_experiments.py` never told the judge what the real taxonomy was — it graded against its own
free-form expectation instead. `enhancement` is a defensible pick given the current
`classify_system` rules (a version of the reason-code capability already ships today).
**Fix:** rewrote `_AGENT_RUBRIC["solution_architect"]` to enumerate the actual 6 categories and
explicitly instruct the judge not to penalize a defensible pick among them just because a more
specific external label would also describe the BRD. `classify_system` itself was left unchanged —
this was a rubric problem, not a prompt problem, and changing the wrong side would have masked the
real issue for future BRDs.

**Status:** both fixes applied, not yet re-scored.

---

## 10. Iteration 4 — the biggest bug of all was in the judge, not any agent

Asked "why do the *other* agents also score badly on llm_quality" and checked each one against real
data instead of trusting the judge's text. Found the evaluator itself was the dominant cause.

**The bug:** `llm_quality()` in `run_experiments.py` truncated both the BRD excerpt and the agent
output to a flat 2500 characters before showing them to the judge. Measured against the real data:

| | Size | vs. 2500-char cap |
|---|---|---|
| BRD files | 4,129–5,349 chars | mostly over — and for 2 of 4 BRDs, the **entire Functional Requirements table** fell past byte 2500 and was never shown to the judge at all |
| `plan_generator` output | up to 14,029 chars | judge saw ~18% of it |
| `solution_architect` output | up to 13,316 chars | judge saw ~19% of it |
| `schedule_estimator` output | up to 14,047 chars | judge saw ~18% of it |
| `tech_stack_recommender` output | up to 6,639 chars | judge saw ~38% of it |

This alone explains most of the recurring complaints: *"the excerpt is truncated," "phase ordering
is only partially visible," "omits requirements"* — the judge was often grading maybe a fifth of
what the agent actually produced, then penalizing the agent for gaps that were invisible-to-judge,
not actually missing. **Fix:** raised the BRD cap to 8,000 chars (covers all 4 golden BRDs whole)
and the output cap to 16,000 chars (covers every agent's observed max with headroom).

**A second, related bug:** `tech_stack_recommender`'s rubric asks the judge to check that the
recommendation "primarily reuses Arbor's existing services" — but the judge was never given Arbor's
actual stack (`rag/sources/current_tools_and_stack.md`). It was guessing from general software
knowledge. Checked the real stack doc: **SQS, SNS, Snowflake, dbt, Redis (ElastiCache), DynamoDB,
and Auth0 are all already part of Arbor's existing stack** — yet the judge penalized outputs for
"introducing new infrastructure... SQS... Snowflake, Redis," which is factually wrong. This also
explains the wild score variance for the same BRD across repeated runs (0.2 and 0.9 for the same
`brd_application_fraud_scoring` example) — an ungrounded judge is an inconsistent judge.
`solution_architect`'s rubric has the same "named from RAG context" check and the same blind spot.
**Fix:** inject the actual stack doc into the judge prompt for both agents so "existing vs. new" is
checked against ground truth, not guesswork.

**Two real agent-side bugs also confirmed** (not evaluator artifacts — verified against actual BRD
text and actual agent output):
- `plan_generator` (`brd_first_party_fraud_case_management`): judge said it added "out-of-scope"
  items (S3 object-lock/WORM, SLOs, retry policies, monthly verification reports). Checked the
  BRD's real out-of-scope section — none of those four things are even mentioned there or anywhere
  in the BRD. They're invented implementation specifics, not out-of-scope features — a distinct
  failure mode from what the v1.1.0 SCOPE ENFORCEMENT rule targets. **Fix:** added a NO INVENTED
  IMPLEMENTATION SPECIFICS rule (v1.2.0) — a deliverable may reference a real requirement in general
  terms without inventing the concrete mechanism used to satisfy it.
- `critic`: revision_notes were consistently "too vague... doesn't tell the generator exactly what
  to change," and unlike the other agents, critic's own output was never truncated — this complaint
  held up. The original instruction ("specific, actionable fixes") had no REQUIREMENT tag or
  Bad-example anchor, unlike every other agent's prompt. **Fix:** added the same REQUIREMENT +
  Good/Bad pattern used elsewhere (critic v1.1.0).

**Status:** all four fixes applied (evaluator truncation, evaluator stack-grounding, plan_generator
v1.2.0, critic v1.1.0), not yet re-scored.

---

## 11. Key lessons for multi-agent prompt improvement

1. **Vague directives don't stick.** "Respect out-of-scope" and "ground in company stack" produced 0.20 scores. The model needs explicit, enumerated constraints with examples of failure.

2. **Don't fix "model ignores RAG" by duplicating RAG in the system prompt.** If the RAG sources already contain the right names and retrieval routing is correct, the fix is to teach the model HOW to use the context faithfully ("copy verbatim from context above"), not to repeat the knowledge base in the prompt. Hardcoding the stack creates a maintenance burden and breaks the single-source-of-truth principle.

3. **REQUIREMENT vs. Rule.** Calling something a REQUIREMENT with concrete bad examples (not just good examples) is significantly more constraining than a rule buried in a bullet list.

4. **Structural axes for differentiation.** Telling the model "options must be genuinely different" is not enough. Specifying the axes of difference (processing model, deployment unit, data pattern) gives the model a concrete checklist to diverge on.

5. **Traceability as a pre-flight check.** Prompting the model to verify each BRD requirement maps to a deliverable before finalising catches omissions that instruction-following alone misses.

6. **One judge explanation = one prompt fix.** Each distinct LLM judge failure maps to exactly one missing constraint in the prompt. The fix should be targeted — don't add generic "be more specific" instructions.

7. **A prompt fix cannot compensate for missing context.** `schedule_estimator`'s v1.1.0 prompt change (REQUIREMENT tags, concrete examples) produced **zero measurable improvement** — 0.20 before, 0.20 after, identical judge complaint. The instructions were fine; the model simply never received the facts it was being told to cite, because `_format_brd()` only forwarded 3 of 12 BRD section types. Before rewriting a prompt in response to a low judge score, check what the model actually receives — grep the context-assembly function, don't just re-read the prompt. If the judge is asking for a fact and the score doesn't move after you told the model to include it, the fact probably isn't in its context at all.

8. **Don't let a few-shot example encode the eval's expected answer.** The original "Good" assumption example hardcoded the exact headcount and role breakdown that matched the golden BRD's judge rubric. That's fragile (teaches to one test case) and masked the real bug (it looked like a prompting problem when it was a data problem). Few-shot examples should illustrate a *pattern* ("cite the real number from context, or say you're estimating"), not assert one BRD's specific answer as if it generalizes.

9. **Build the local, terminal-based comparison loop before you need it at scale.** Screenshotting the Phoenix UI for every iteration doesn't scale past a couple of cycles. `run_experiments.py` now writes `llm_quality` scores *and* judge explanations into the JSON snapshot, and `compare_experiments.py --latest --explanations` diffs two runs from the terminal — screenshots are reserved for the article, not the iteration loop itself.

10. **Pull the raw agent output before trusting the judge's diagnosis.** The judge's one-sentence explanation is a summary, not ground truth — it can be right for the wrong reason or wrong outright. Reading the actual `solution_architect` output directly from the Phoenix dataset showed the differentiation complaint was correct (options A and C really did share a critical-path design) but the problem_type complaint was not (it graded against a category that isn't in the agent's own taxonomy). Treat a low score as a pointer to go look, not as an instruction to edit the nearest prompt.

11. **A bad score has two possible root causes: the agent, or the judge.** When a judge complaint doesn't survive a look at the real taxonomy/constraints the agent is operating under, the fix belongs in the eval rubric (`_AGENT_RUBRIC` in `run_experiments.py`), not the agent's prompt. Editing `classify_system` to chase a category that will never exist would have "fixed" the score while making the classifier worse for every other BRD — the eval harness needs to be graded for correctness too, not just the pipeline it's grading.

12. **Check the judge's context window before touching a single prompt.** A flat character-truncation cap in the evaluator (2500 chars for both the BRD and the agent output) was hiding up to 82% of what verbose agents actually produced, and cutting the Functional Requirements table out of 2 of 4 golden BRDs entirely. Every low score across `plan_generator`, `solution_architect`, `schedule_estimator`, and `tech_stack_recommender` was, to some non-trivial degree, downstream of this one evaluator bug. If several unrelated agents all score badly on the same evaluator in similar-sounding ways ("truncated," "partially visible," "omits"), suspect the evaluator's plumbing before suspecting four separate agents independently developed the same problem.

13. **"Grounded in company context" cuts both ways — the judge needs the grounding too.** `tech_stack_recommender` and `solution_architect` were both graded on whether they "reuse Arbor's existing services," but the judge itself was never given Arbor's stack list — it graded from general knowledge and got it wrong (penalizing SQS, Snowflake, and Redis as "new" when they're already in Arbor's stack), with visible run-to-run score variance as a symptom. Any rubric that says "check against X" requires X to actually be in the judge's prompt, not just referenced by name.
