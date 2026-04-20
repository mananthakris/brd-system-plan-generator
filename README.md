# BRD → Engineering System Plan — Multi-Agent Pipeline

A multi-agent system that ingests Business Requirements Documents (BRDs, PRDs, RFCs) and produces structured engineering system plans. Built with LangGraph and OpenAI, evaluated against **Verdant Intelligence** — a fictional energy benchmarking and compliance SaaS company.

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
  Planning group          Design group
  ├── Plan Generator      ├── Solution Architect (classifies problem type)
  └── Schedule Estimator  ├── PoC Planner (conditional)
                          └── Tech Stack Recommender
      ↓
  Critic Agent (rubric scoring, up to 2 revision cycles)
      ↓
  HITL Gate (EM approval)
      ↓
  Engineering System Plan (PDF / Markdown)
```

All agents retrieve context from a RAG pipeline (Chroma + `text-embedding-3-small`) seeded with the company's architecture decision records, current stack, team skills, cloud infrastructure docs, and domain knowledge.

---

## Evaluation company: Verdant Intelligence

A fictional ~52-person energy compliance SaaS company based in Chicago. Their platform helps building owners track carbon emissions and forecast penalties under NYC Local Law 97, Chicago BEPO, and Boston BERDO.

The included sample BRD — **Automated Carbon Penalty Forecasting Engine** (`rag/sources/brd_penalty_forecasting_engine.md`) — is the primary evaluation artifact for this project.

**Tech stack (used to seed RAG):**
- Backend: Python / FastAPI / PostgreSQL (Aurora) / Celery
- Data: Snowflake / dbt / Airflow (MWAA)
- Infrastructure: AWS (ECS Fargate, S3, SQS, Lambda) / Terraform
- Frontend: React / TypeScript

---

## Project structure

```
capstone-project/
├── agents/
│   ├── orchestrator.py       # LangGraph graph — full wiring, stub node implementations
│   ├── planning/             # Phase 2: plan_generator.py, schedule_estimator.py
│   └── design/               # Phase 2: solution_architect.py, poc_planner.py, tech_stack_recommender.py
├── ingestion/
│   ├── parser.py             # PDF / DOCX / MD → raw text
│   ├── classifier.py         # GPT-4o-mini section classifier
│   ├── tagger.py             # GPT-4o-mini metadata tagger
│   └── pipeline.py           # Composed ingestion entry point
├── rag/
│   ├── pipeline.py           # Chroma client, embed, retrieve
│   ├── seed.py               # Seed knowledge base from sources/
│   └── sources/              # RAG knowledge base (Markdown files)
│       ├── architecture_decisions.md
│       ├── current_tools_and_stack.md
│       ├── team_skills.md
│       ├── cloud_infrastructure.md
│       ├── domain_context_energy_compliance.md
│       └── brd_penalty_forecasting_engine.md   ← primary eval BRD
├── schemas/
│   └── models.py             # All Pydantic models + LangGraph GraphState
├── state/
│   └── store.py              # SQLite checkpointer, session + revision + HITL audit store
├── guardrails/
│   └── checks.py             # Input validation, injection detection, output schema checks
├── output/                   # Phase 4: formatter.py, exporter.py
├── docs/
│   ├── ARCHITECTURE.md       # Runtime topology with diagram
│   └── runtime_topology_v2.svg
├── config.py                 # Pydantic settings (reads .env)
├── main.py                   # CLI entry point
└── requirements.txt
```

---

## Setup

**1. Install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp .env.example .env
# Set OPENAI_API_KEY in .env
```

**3. Run the demo**

Ingests the built-in Penalty Forecasting BRD through the full pipeline:

```bash
python main.py --demo
```

**4. Run with your own BRD**

```bash
# From a file (.pdf, .docx, .md, .txt)
python main.py --brd-file path/to/your_brd.md --title "My Feature"

# From inline text
python main.py --brd-text "$(cat your_brd.txt)"
```

**5. Seed the RAG knowledge base independently**

```bash
# Seed (idempotent — safe to run multiple times)
python -m rag.seed

# Reset and rebuild
python -m rag.seed --reset
```

---

## Build phases

| Phase | Status | Scope |
|---|---|---|
| 1 | **Complete** | Skeleton: ingestion, RAG pipeline, schemas, state store, guardrails, LangGraph graph wiring |
| 2 | Upcoming | Real agent implementations: Plan Generator, Schedule Estimator, Solution Architect, PoC Planner, Tech Stack Recommender |
| 3 | Upcoming | Critic Agent with rubric scoring; revision loop |
| 4 | Upcoming | HITL gate (`interrupt()`), output formatter, PDF/MD export |
| 5 | Upcoming | Guardrails hardening, cross-agent consistency checks |
| Evals | Later | Offline eval harness against Verdant Intelligence BRDs; rubric schema already defined in `CriticRubric` |

---

## Key design decisions

**LangGraph for orchestration** — Native hub-and-spoke topology, built-in state persistence via SQLite checkpointer, `interrupt()` for HITL, and conditional edges for the critic revision loop. No custom loop management.

**Problem type classification gates the graph** — The Solution Architect classifies the BRD as `greenfield | migration | integration | poc | enhancement` before any design work. This single field controls whether the PoC Planner runs and how the final output is sized.

**Dual model strategy** — `gpt-4o` for Orchestrator, Solution Architect, and Critic (judgment-heavy). `gpt-4o-mini` for Schedule Estimator, PoC Planner, Tech Stack Recommender (structured output from clear inputs).

**RAG retrieval at agent level, not graph level** — Each agent issues its own retrieval query tuned to its task. The Orchestrator does not pre-fetch; agents pull exactly what they need (top-k=5, cosine similarity ≥ 0.75).

**Critic rubric defined upfront** — `CriticRubric` schema in `schemas/models.py` has 5 scored dimensions (completeness, feasibility, specificity, consistency, scope_fit). This same schema will drive the offline eval harness in a later phase.

---

## Adding to the RAG knowledge base

Drop any `.md` or `.txt` file into `rag/sources/` and re-run `python -m rag.seed`. File names control the source type assigned in Chroma metadata:

| Filename prefix | Source type |
|---|---|
| `architecture_*` | `architecture_decision` |
| `current_tools_*` | `current_stack` |
| `team_skills_*` | `team_skills` |
| `cloud_*` | `cloud_infrastructure` |
| `brd_*` / `prd_*` | `past_brd` |
| `plan_template_*` | `plan_template` |
| `eng_standards_*` | `eng_standards` |
| anything else | `domain_context` |
