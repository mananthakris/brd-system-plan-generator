# Developer Setup Guide

## Prerequisites

- Python 3.11+ (the project uses `list[str]` and `X | Y` union syntax; 3.9 will fail)
- An OpenAI API key with access to the models in your `.env` (`ORCHESTRATOR_MODEL`, `FAST_MODEL`, `EMBEDDING_MODEL`)

Check your Python version:
```bash
python3.12 --version
```

If you need to install a newer version, use [pyenv](https://github.com/pyenv/pyenv):
```bash
brew install pyenv
pyenv install 3.12
pyenv local 3.12
```

---

## 1. Create and activate a virtual environment

```bash
cd capstone-project

python3.12 -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows
```

You should see `(.venv)` in your prompt. All commands below assume the venv is active.

---

## 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

First install takes 2–3 minutes — `chromadb` and `weasyprint` are the slow ones.

Verify the key packages installed:
```bash
python3.12 -c "import langchain, langgraph, chromadb, openai; print('ok')"
```

---

## 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set at minimum:
```
OPENAI_API_KEY=sk-...
```

All other values have sensible defaults. Notable overrides:

| Variable | Default | When to change |
|---|---|---|
| `ORCHESTRATOR_MODEL` | `gpt-5.4` | Swap to `FAST_MODEL` value to cut cost during dev |
| `AGENT_MODEL` | `gpt-5.4` | Same |
| `CHROMA_PERSIST_DIR` | `.chroma` | Change if you want the DB elsewhere |
| `RAG_SCORE_THRESHOLD` | `0.75` | Lower to `0.5` if retrieval returns nothing |
| `MAX_REVISION_CYCLES` | `2` | Set to `0` to skip the critic revision loop |

---

## 4. Seed the RAG knowledge base

This loads the Arbor Risk knowledge base (architecture decisions, team skills, cloud infra, domain context, sample BRD) into ChromaDB. It is idempotent — safe to run multiple times.

```bash
python3.12 -m rag.seed
```

To wipe and rebuild from scratch:
```bash
python3.12 -m rag.seed --reset
```

Expected output:
```
Seeding from .../rag/sources
  seeded architecture_decisions.md → 9 chunks [architecture_decision]
  seeded brd_penalty_forecasting_engine.md → 12 chunks [past_brd]
  seeded cloud_infrastructure.md → 8 chunks [cloud_infrastructure]
  seeded current_tools_and_stack.md → 7 chunks [current_stack]
  seeded domain_context_energy_compliance.md → 10 chunks [domain_context]
  seeded team_skills.md → 6 chunks [team_skills]

✓ Seeded 52 new chunks. Collection total: 52
```

---

## 5. Run agent tests

Each agent has an isolated test script in `tests/`. These run the agent directly — no full graph, no other agents. This is the right way to test one agent at a time during Phase 2 development.

### Solution Architect

The only real agent implemented so far. Tests classification + architecture design against the Penalty Forecasting BRD.

```bash
python3.12 -m tests.test_solution_architect
```

What it does:
1. Seeds RAG (idempotent)
2. Ingests `rag/sources/brd_penalty_forecasting_engine.md`
3. Runs the Solution Architect (two GPT-4o calls: classify → design)
4. Validates output schema and guardrails
5. Prints problem type, components, data flow, integration points, constraints addressed

Expected runtime: ~15–25 seconds (two GPT-4o calls + embedding retrieval).

### Running pytest (unit tests)

For tests that don't need live API calls:
```bash
pytest tests/ -v
```

To skip tests that require OpenAI:
```bash
pytest tests/ -v -m "not integration"
```

To run a single test file:
```bash
pytest tests/test_solution_architect.py -v
```

---

## 6. Run the full pipeline

### Demo mode (uses the built-in Penalty Forecasting BRD)

```bash
python3.12 main.py --demo
```

The `--skip-seed` flag skips RAG seeding if you've already run it:
```bash
python3.12 main.py --demo --skip-seed
```

### From a file

```bash
python3.12 main.py --brd-file path/to/your_brd.md --title "Feature Name"
```

Supported formats: `.pdf`, `.docx`, `.md`, `.txt`

### From inline text

```bash
python3 main.py --brd-text "$(cat your_brd.txt)" --title "Feature Name"
```

### Resume a session

Each run creates a session ID. Pass it to resume from a LangGraph checkpoint:
```bash
python3.12 main.py --brd-file your_brd.md --session-id <session-id-from-prior-run>
```

---

## 7. Run the UI

The UI is a Vite + React frontend talking to a FastAPI backend over SSE.

### Install frontend dependencies (first time only)

```bash
cd frontend
npm install
cd ..
```

### Start the backend (terminal 1)

```bash
source .venv/bin/activate
venv/bin/python -m uvicorn api.server:app --reload --port 8000
```

On startup the server seeds the RAG knowledge base automatically.
Expected output:
```
Seeding RAG knowledge base...
  seeded architecture_decisions.md → ...
  ...
RAG ready.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Start the frontend (terminal 2)

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Using the UI

1. Paste a BRD or upload a file (`.pdf`, `.docx`, `.md`, `.txt`)
2. Enter a title and click **Run pipeline**
3. Watch the pipeline status panel on the left update in real time via SSE
4. The Solution Architect output card appears once that agent completes (~15–25 s)
5. Stub agent cards appear greyed out — they fill in as Phase 2 agents are implemented

---

## 8. Running evals

The eval harness runs the full pipeline against 4 golden fraud-domain BRDs and scores every agent output through two independent paths:

- **Structural checks** — rule-based, no LLM cost, always available
- **LLM-as-Judge** — GPT-4o-mini scores each agent's output against a rubric, results posted back to Phoenix as span annotations

The full cycle is: generate traces → build a dataset → score spans → identify failures → fix prompts → re-run → compare scores. The sections below walk through each step in order.

---

### Step 1 — start Phoenix (keep this terminal open)

Phoenix must be running as a persistent server before you run any eval scripts. Open a dedicated terminal:

```bash
venv/bin/python -m phoenix.server.main serve
```

Leave this running. Open `http://localhost:6006` — you should see the Phoenix home screen. All subsequent steps depend on Phoenix being up.

---

### Step 2 — generate traces (run the golden BRDs)

In a **second terminal**:

```bash
venv/bin/python -m evals.run_golden_brds
```

What it does:
- Verifies Phoenix is reachable (exits early if not)
- Seeds the RAG knowledge base (idempotent)
- Runs all 4 golden BRDs through the full pipeline
- Each agent node emits an `AGENT`-kind span with `input` (BRD text + context) and `output` (agent JSON) populated
- Prints `critic_score` and `revision_count` per BRD
- Writes `evals/results/golden_brd_run.json`

Expected runtime: ~2–4 minutes (4 full pipeline runs).

After this completes you will see spans in Phoenix UI at `http://localhost:6006` → **brd-planner** project → **Spans** tab. Each agent (`plan_generator`, `solution_architect`, etc.) appears as an `AGENT`-kind span with populated `input` and `output` columns.

---

### Step 3 — dataset creation (automatic)

`run_golden_brds.py` creates the eval dataset for you automatically — no UI steps needed. Phoenix's "Add to Dataset" UI only works for `LLM`-kind spans; it silently skips `AGENT`-kind spans, so dataset creation is done via the Python client instead.

The script builds **one example per agent per BRD** (4 BRDs × 5 agents = 20 examples) and upserts a dataset named `golden_brd_evals` in Phoenix:

| Example field | Contents |
|---|---|
| `input` | `agent_name`, `brd_filename`, `brd_title`, `brd_text` (first 5000 chars) |
| `output` | the agent's structured `content` dict from that run |
| `metadata` | `brd_id`, `critic_score`, `revision_count` |

On the first run the dataset is created. On subsequent runs a new version is added (Phoenix datasets are versioned — the evaluator always uses the latest version).

View the dataset: `http://localhost:6006` → **Datasets & Experiments** → `golden_brd_evals`.

---

### Step 4 — structural checks (no Phoenix required)

```bash
venv/bin/python -m evals.run_structural_checks
```

Runs 6 agents in isolation against the golden BRDs and applies rule-based checks — no LLM calls, no network. Useful for fast feedback during prompt editing.

| Agent | Checks |
|---|---|
| plan_generator | phase_count_in_range · all_phases_have_deliverables · scope_boundary |
| schedule_estimator | duration_set · risk_entries_present · assumptions_nonempty |
| solution_architect | 2–3 options · unique IDs · valid problem_type · schema_valid |
| tech_stack_recommender | options_present · recommended_option_set · rationale_nonempty |
| critic | all_five_dimensions · scores_in_range · revision_notes_present |
| output_formatter | exec_summary_present · sections_complete · schema_valid |

Results print as a Rich table (green ✓ / red ✗ per check) and are saved to `evals/results/structural_check_results.json`.

Pass-rate thresholds: **≥ 80% = green**, ≥ 60% = amber, < 60% = red.

---

### Step 5 — (optional) verify spans before evaluating

```bash
venv/bin/python -m evals.run_phoenix_evals
```

Prints a diagnostic table: span counts by kind, and per agent — how many spans exist and whether `input`/`output` are populated. Use this to confirm the traces from Step 2 look correct before running the experiment.

---

### Step 5 — run the LLM-as-Judge experiment

```bash
venv/bin/python -m evals.run_experiments
```

Loads the `golden_brd_evals` dataset and runs `client.experiments.run_experiment()` with three evaluators against all 20 examples (4 BRDs × 5 agents):

| Evaluator | Type | What it measures |
|---|---|---|
| `critic_score` | Rule-based | Normalised critic overall_score from the golden run (0–1) |
| `output_completeness` | Rule-based | Fraction of non-empty fields in the agent output |
| `llm_quality` | LLM judge (`FAST_MODEL`) | Agent-specific rubric score with a cited explanation |

The `llm_quality` rubric is tailored per agent — for example, `solution_architect` is checked for RAG grounding (uses specific service names from context, not generic terms like "message queue"), `plan_generator` for BRD coverage and phase order, `critic` for feedback specificity.

Makes ~20 LLM calls total (one per example). Results appear immediately in the Phoenix UI:

`http://localhost:6006` → **Datasets & Experiments** → `golden_brd_evals` → **Experiments** tab

Each experiment run is versioned — re-run after editing a prompt and the new version appears alongside the old one for direct score comparison.

The script also saves a **local score snapshot** to `evals/results/experiment_<timestamp>.json` tagged with the current prompt versions from `prompts/registry.py`. These snapshots are used by `compare_experiments.py` and do not require Phoenix to be running.

---

### Step 6 — read results in the Phoenix UI

1. Go to `http://localhost:6006` → **Datasets & Experiments** → `golden_brd_evals` → **Experiments**
2. Click the latest experiment run
3. Each row = one example (one agent × one BRD) with scores for all three evaluators
4. Click any low-scoring row → see the `llm_quality` explanation citing the specific failure
5. Filter rows by `input.agent_name` to focus on one agent at a time

---

### The improvement cycle

This is the core loop. Each iteration should move at least one failing evaluator from red to green. Prompts are versioned artifacts in `prompts/registry.py` — every change is traceable to the eval run that validated it.

**1. Find what's failing**

Run the experiments and check the stdout per-agent score summary or Phoenix UI. Find evaluators with avg score below 0.7. Example:
```
solution_architect  llm_quality     0.25   ← fix this
plan_generator      critic_score    0.50   ← fix this
```

**2. Understand why it's failing**

In Phoenix UI: `http://localhost:6006` → Datasets & Experiments → `golden_brd_evals` → Experiments → click a low-scoring row → read the `llm_quality` explanation. It will say something like:
> "The architecture output uses 'message queue' and 'relational database' — generic terms not grounded in Arbor's known stack (Amazon SQS, Aurora Postgres)."

**3. Edit the prompt in the registry and bump the version**

Open `prompts/registry.py`. Find the agent's entry. Edit the prompt and increment the version:

```python
# Before
"solution_architect": {
    "version": "1.0.0",
    "changelog": "Two-step classify-then-design pipeline ...",

# After
"solution_architect": {
    "version": "1.1.0",
    "changelog": "Add explicit stack-grounding rule: name SQS/Aurora/Redis/EKS by service name",
```

Add a targeted instruction to the prompt text. Example:
> "Always name specific services from the company's known stack as provided in context: e.g. Amazon SQS for async job queuing, Aurora Postgres for relational data, Redis for caching, EKS for containerised workloads. Do not use generic terms like 'message queue' or 'database'."

**4. Re-run and compare**

```bash
# Generate new outputs + save a new local snapshot
venv/bin/python -m evals.run_golden_brds && \
venv/bin/python -m evals.run_experiments

# Print before/after score table (no Phoenix required)
venv/bin/python -m evals.compare_experiments --latest
```

The comparison output shows per-agent score deltas and which prompt version changed:

```
  Prompt versions:
    solution_architect             1.0.0  →  1.1.0    ← changed

  Agent                        Evaluator          Baseline Candidate    Delta
  ──────────────────────────────────────────────────────────────────────────
  solution_architect           critic_score         0.6200    0.8100  +0.1900  ✓
  solution_architect           output_completeness  0.8500    0.8800  +0.0300  ✓
  plan_generator               critic_score         0.7200    0.7200  +0.0000  ~

  VERDICT: Scores improved after prompt change(s). Safe to ship.
```

If scores regressed on another agent, that prompt instruction may be conflicting — narrow it and re-run.

**5. Repeat** until all evaluators are consistently ≥ 0.7.

---

**Common prompt fixes by failure type:**

Edit the relevant agent's entry in `prompts/registry.py`, bump the version, and re-run.

| Failure | Prompt fix |
|---|---|
| `brd_coverage` < 0.7 | "Enumerate each functional requirement from the BRD and map it to a specific phase deliverable." |
| `rag_grounding` < 0.7 | "Name specific services from the company tech stack as provided in context (e.g. Amazon SQS, Aurora Postgres, Redis, EKS). Do not use generic terms." |
| `options_genuinely_different` < 0.7 | "Each architectural option must differ in fundamental approach (e.g. event-driven vs. batch, serverless vs. containerised). Configuration differences alone do not count." |
| `feedback_specificity` < 0.7 | "Every feedback point must name the specific phase, component, or deliverable it refers to." |
| `phase_count_in_range` fail | Add to schema or prompt: "Produce between 3 and 6 phases." |
| `assumption_specificity` < 0.7 | "Every assumption must reference specific BRD details: named services, team sizes, or explicit constraints from the document." |

---

## 9. Adding a new agent (Phase 2 pattern)

1. Create `agents/design/<agent_name>.py` or `agents/planning/<agent_name>.py` with a class that has a `run(self, state_dict) -> dict` method returning a serialised `AgentOutput`.
2. Create `tests/test_<agent_name>.py` following the pattern in `tests/test_solution_architect.py`.
3. In `agents/orchestrator.py`, replace the corresponding stub node (e.g. `node_plan_generator`) with a real implementation that calls your new agent class, following the same lambda-closure pattern as `solution_architect`.

---

## Project layout (quick reference)

```
capstone-project/
├── agents/
│   ├── orchestrator.py          # LangGraph graph — edit here to wire new agents
│   ├── design/
│   │   └── solution_architect.py   ← real (Phase 2)
│   └── planning/                   ← stubs (Phase 2 next)
├── ingestion/                   # Parser → classifier → tagger
├── rag/
│   ├── pipeline.py              # Chroma client
│   ├── seed.py                  # Run this to populate knowledge base
│   └── sources/                 # Drop .md/.txt files here to extend RAG
├── schemas/models.py            # All Pydantic models + GraphState
├── state/store.py               # Session + revision + HITL audit log
├── guardrails/checks.py         # Validation applied at every boundary
├── tests/
│   └── test_solution_architect.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── runtime_topology_v2.svg
├── .env.example                 # Copy to .env
├── config.py                    # Settings (reads .env)
├── main.py                      # CLI entry point
└── requirements.txt
```

---

## Common issues

**`ModuleNotFoundError` on any import**
Run all commands from the `capstone-project/` root with the venv active. The project uses relative imports and expects the root to be on `sys.path`.

**`chromadb` collection errors on first run**
The `.chroma/` directory is created automatically. If you see a schema mismatch error after updating ChromaDB, run `python3 -m rag.seed --reset` to rebuild.

**OpenAI rate limit errors**
The agent calls in `solution_architect.py` are sequential (classify, then design) — no parallelism to cause burst. If you hit rate limits, set `ORCHESTRATOR_MODEL` to your `FAST_MODEL` value in `.env` for development.

**RAG returning no results (empty `retrieved_chunks`)**
Lower `RAG_SCORE_THRESHOLD` to `0.5` in `.env` and re-run. If still empty, confirm the seed ran successfully with `python3 -m rag.seed`.

**`with_structured_output` parsing errors**
Intermittent JSON parse failures from the LLM. Re-running usually resolves it. If persistent, the model may be hitting a context limit — try shortening the BRD input.
