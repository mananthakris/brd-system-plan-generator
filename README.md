# BRD → Engineering System Plan — Multi-Agent Pipeline

A multi-agent system that ingests Business Requirements Documents (BRDs, PRDs, RFCs) and produces decision-ready engineering plans with competing architectural options. Built with LangGraph and OpenAI, evaluated against **Arbor Risk** — a fictional fraud detection and risk decisioning platform.

→ [Runtime Topology & Architecture](docs/ARCHITECTURE.md)

---

## What it does

```
BRD / PRD / RFC
      ↓
  Ingestion (parse → classify sections → tag metadata)
      ↓
  Orchestrator (LangGraph hub-and-spoke)
      ↓
  Planning group              Design group
  ├── Plan Generator          ├── Solution Architect (classify → 2-3 competing options + recommendation)
  └── Schedule Estimator      ├── PoC Planner (conditional on problem_type == poc)
                              └── Tech Stack Recommender
      ↓
  Critic Agent (5-dimension rubric, up to 2 revision cycles)
      ↓
  HITL Gate (Engineering Manager approval via interrupt())
      ↓
  Output Formatter (executive summary + assembled engineering plan)
```

All agents retrieve context from a RAG pipeline (ChromaDB + `text-embedding-3-small`) seeded with Arbor Risk's architecture decisions, current stack, team skills, cloud infrastructure docs, domain knowledge, and compliance standards.

---

## Evaluation company: Arbor Risk

A fictional fraud detection and risk decisioning platform serving banks, card issuers, payment processors, and lending platforms. Arbor operates in-house ML models (XGBoost, LightGBM, PyTorch GNN) on AWS, scoring transactions at < 80ms p99.

**Tech stack used to seed the RAG knowledge base:**

| Layer | Technologies |
|---|---|
| Async messaging | Amazon SQS (job queue) · SNS · Celery + Redis (background tasks) |
| Feature store | Tecton (online: ElastiCache Redis · offline: S3 + Spark) |
| ML inference | FastAPI on EKS (XGBoost/LightGBM in-memory, p99 < 40ms) |
| Databases | Aurora PostgreSQL · DynamoDB · ElastiCache Redis |
| Data platform | Snowflake + dbt · Apache Spark on EMR · Airflow (MWAA) |
| API | FastAPI (Python 3.12) · Gin (Go) · gRPC |
| Infrastructure | AWS EKS (Graviton) · Terraform · ArgoCD |
| Observability | Datadog · Evidently AI |

**Four golden eval BRDs (in `rag/sources/`):**

| BRD | Feature |
|---|---|
| `brd_adverse_action_reason_codes.md` | ReasonIQ v1 — FCRA reason code engine |
| `brd_application_fraud_scoring.md` | ScoreIQ v2 — async scoring pipeline |
| `brd_first_party_fraud_case_management.md` | CaseTrack v2 — analyst workbench + SAR |
| `brd_synthetic_identity_detection.md` | IdentityGraph v1 — synthetic identity ML |

---

## Project structure

```
capstone-project/
├── agents/
│   ├── orchestrator.py            # LangGraph graph — full wiring + OpenInference AGENT spans
│   ├── critic.py                  # 5-dimension rubric scorer, triggers revision loop
│   ├── planning/
│   │   ├── plan_generator.py      # phased project plan from BRD + RAG context
│   │   └── schedule_estimator.py  # timeline, risks, assumptions
│   ├── design/
│   │   ├── solution_architect.py  # problem classification + 2-3 competing arch options
│   │   └── tech_stack_recommender.py  # stack recommendations grounded in Arbor's stack
│   └── output/
│       └── formatter.py           # executive summary + final plan assembly
├── ingestion/
│   ├── parser.py                  # PDF / DOCX / MD / TXT → raw text
│   ├── classifier.py              # section classifier (FAST_MODEL)
│   ├── tagger.py                  # metadata tagger (FAST_MODEL)
│   └── pipeline.py                # composed ingestion entry point
├── rag/
│   ├── pipeline.py                # ChromaDB client — embed + retrieve
│   ├── seed.py                    # seed knowledge base from sources/
│   └── sources/                   # 11 Markdown knowledge base files
├── prompts/
│   └── registry.py                # versioned prompt store — all agent system prompts live here
├── evals/
│   ├── run_golden_brds.py         # run 4 BRDs through full pipeline, create Phoenix dataset
│   ├── run_experiments.py         # LLM-as-judge + saves local score snapshot tagged with prompt versions
│   ├── compare_experiments.py     # before/after score diff CLI (no Phoenix required)
│   ├── run_structural_checks.py   # rule-based checks, no LLM calls
│   ├── run_phoenix_evals.py       # span diagnostic report
│   ├── phoenix_evals/
│   │   └── evaluators.py          # LLM-as-judge prompt templates per agent
│   ├── results/                   # local score snapshots (experiment_<timestamp>.json)
│   └── structural/                # per-agent rule-based check modules
├── schemas/
│   └── models.py                  # all Pydantic models + LangGraph GraphState
├── state/
│   └── store.py                   # SQLite checkpointer, session + HITL audit log
├── guardrails/
│   └── checks.py                  # input validation, injection detection, output schema checks
├── api/
│   └── server.py                  # FastAPI backend with SSE streaming
├── frontend/                      # React + Vite + Tailwind UI
├── docs/
│   ├── ARCHITECTURE.md
│   └── runtime_topology_v2.svg
├── config.py                      # pydantic-settings (reads .env)
├── main.py                        # CLI entry point
├── .env.example                   # copy to .env, set OPENAI_API_KEY
└── requirements.txt
```

---

## Setup

**1. Create virtualenv and install dependencies**

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY at minimum
```

**3. Seed the RAG knowledge base**

```bash
venv/bin/python -m rag.seed
```

**4. Run the pipeline**

```bash
# Demo mode (uses built-in BRD)
venv/bin/python main.py --demo

# From a file
venv/bin/python main.py --brd-file path/to/your_brd.md --title "Feature Name"
```

**5. Run the UI**

```bash
# Terminal 1 — backend
venv/bin/python -m uvicorn api.server:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm install && npm run dev
# Open http://localhost:5173
```

---

## Eval harness

Scores all agents against 4 golden Arbor Risk BRDs. Prompts are versioned artifacts in `prompts/registry.py` — every eval run is tagged with which prompt version produced the scores, enabling before/after comparison.

```bash
# Terminal 1 — start Phoenix (keep running)
venv/bin/python -m phoenix.server.main serve

# Terminal 2 — run pipeline + create dataset + run evaluations
venv/bin/python -m evals.run_golden_brds       # ~2-4 min, creates golden_brd_evals dataset
venv/bin/python -m evals.run_structural_checks  # rule-based, instant
venv/bin/python -m evals.run_experiments        # LLM-as-judge (~20 API calls) + saves local snapshot
```

Results appear in Phoenix UI at `http://localhost:6006` → Datasets & Experiments → `golden_brd_evals` → Experiments tab. Each run is versioned — re-run after a prompt change and scores appear side-by-side.

**Eval-driven improvement workflow:**

```bash
# 1. Run baseline
venv/bin/python -m evals.run_experiments

# 2. Edit prompts/registry.py — change a prompt, bump its version (e.g. "1.0.0" → "1.1.0")

# 3. Re-run
venv/bin/python -m evals.run_golden_brds && venv/bin/python -m evals.run_experiments

# 4. Compare before/after (no Phoenix required)
venv/bin/python -m evals.compare_experiments --latest
```

**Evaluators per agent:**

| Agent | LLM-judge rubric | Structural checks |
|---|---|---|
| plan_generator | brd_coverage · phase_coherence · scope_respect | phase_count · deliverables · scope_boundary |
| solution_architect | classification_accuracy · options_differentiated · rag_grounding | 2-3 options · unique IDs · valid problem_type |
| tech_stack_recommender | existing_stack_preference · constraint_respect | options_present · recommended_set · rationale |
| schedule_estimator | risk_mitigation_quality · assumption_specificity | duration_set · risk_entries · assumptions |
| critic | feedback_specificity · revision_notes_actionability | all_5_dimensions · scores_in_range |
| output_formatter | business_clarity · technical_accuracy | exec_summary · sections_complete |

---

## Key design decisions

**LangGraph for orchestration** — Native hub-and-spoke topology with built-in state persistence (SQLite checkpointer), `interrupt()` for HITL, and conditional edges for the critic revision loop.

**Problem type classification gates the graph** — Solution Architect classifies the BRD as `greenfield | new_feature | migration | integration | poc | enhancement` before any design work. This single field controls whether PoC Planner runs and how the output is sized.

**Dual model strategy** — `ORCHESTRATOR_MODEL` (gpt-5.4) for judgment-heavy agents (Solution Architect, Critic). `AGENT_MODEL` for structured-output agents (Plan Generator, Schedule Estimator, Tech Stack Recommender). `FAST_MODEL` (gpt-5.4-mini) for ingestion classifiers and LLM-as-judge evals.

**RAG retrieval at agent level** — Each agent issues its own retrieval query tuned to its task (top-k=5, cosine similarity ≥ 0.75). The Orchestrator does not pre-fetch.

**Critic drives revision** — The Critic scores all upstream outputs on 5 dimensions (completeness, feasibility, specificity, consistency, scope_fit). If `revision_required=true` and `revision_count < MAX_REVISION_CYCLES`, the graph loops back to plan_generator with revision notes.

**OpenInference AGENT spans** — Each orchestrator node wraps its agent call in an explicit OTEL span (`openinference.span.kind=AGENT`) with `input.value` and `output.value` set. This is required for Phoenix to show per-agent traces with populated input/output columns. The eval dataset is created programmatically — Phoenix's "Add to Dataset" UI only processes LLM-kind spans.

---

## Extending the RAG knowledge base

Drop any `.md` or `.txt` file into `rag/sources/` and re-run `venv/bin/python -m rag.seed`. Filename prefix controls the `source_type` metadata tag in Chroma:

| Prefix | Source type |
|---|---|
| `architecture_*` | `architecture_decision` |
| `current_tools_*` | `current_stack` |
| `team_skills_*` | `team_skills` |
| `cloud_*` | `cloud_infrastructure` |
| `brd_*` / `prd_*` | `past_brd` |
| `plan_template_*` | `plan_template` |
| `eng_standards_*` | `eng_standards` |
| anything else | `domain_context` |
