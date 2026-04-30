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
  Planning group          Design group
  ├── Plan Generator      ├── Solution Architect (classify → 2-3 competing options + recommendation)
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

## Evaluation company: Arbor Risk

A fictional fraud detection and risk decisioning platform serving banks, card issuers, payment processors, and lending platforms. Arbor operates in-house ML models (XGBoost, LightGBM, PyTorch GNN) on AWS, scoring transactions in < 80ms p99 via an ensemble of rules, gradient boosting, and network graph signals.

**Five sample BRDs (in `rag/sources/`):**
| BRD | Problem type |
|---|---|
| Real-Time Transaction Scoring Engine | new_feature |
| Velocity Rules Configurator (RuleForge v2) | new_feature |
| Account Takeover Detection Service | new_feature |
| Dispute & Chargeback Automation (CaseTrack v2) | new_feature |
| Model Explainability & Reason Codes | new_feature |

**Tech stack (used to seed RAG):**
- Event streaming: Apache Kafka on MSK + Confluent Schema Registry (Avro)
- Feature store: Tecton (online: ElastiCache Redis · offline: S3 + Spark)
- ML inference: FastAPI on EKS (XGBoost/LightGBM in-memory, p99 < 40ms)
- Databases: Aurora PostgreSQL · DynamoDB · ElastiCache Redis
- Data: Snowflake + dbt · Apache Spark on EMR · Airflow (MWAA)
- API: FastAPI (Python 3.12) · Gin (Go) · gRPC
- Infrastructure: AWS EKS (Graviton) · Terraform · ArgoCD
- Observability: Datadog · Evidently AI · LangSmith

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
│   ├── classifier.py         # GPT-5.4-mini section classifier
│   ├── tagger.py             # GPT-5.4-mini metadata tagger
│   └── pipeline.py           # Composed ingestion entry point
├── rag/
│   ├── pipeline.py           # Chroma client, embed, retrieve
│   ├── seed.py               # Seed knowledge base from sources/
│   └── sources/              # RAG knowledge base (Markdown files)
│       ├── architecture_decisions.md         # 8 Arbor Risk ADRs
│       ├── current_tools_and_stack.md        # full Arbor stack reference
│       ├── cloud_infrastructure.md           # AWS topology + SLAs
│       ├── team_skills.md                    # team composition + gaps
│       ├── domain_context_fraud_detection.md # fraud domain + regulatory context
│       ├── fraud_pattern_library.md          # fraud attack patterns + detection signals
│       ├── compliance_standards.md               # FCRA · ECOA · GLBA · BSA/AML · GDPR · SOC 2
│       ├── brd_application_fraud_scoring.md      # ScoreIQ v2 — async scoring pipeline
│       ├── brd_synthetic_identity_detection.md   # IdentityGraph v1 — synthetic identity ML
│       ├── brd_adverse_action_reason_codes.md    # ReasonIQ v1 — FCRA reason code engine
│       └── brd_first_party_fraud_case_management.md  # CaseTrack v2 — analyst workbench + SAR
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

Ingests the Real-Time Transaction Scoring BRD through the full pipeline:

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
| Evals | Later | Offline eval harness against Arbor Risk BRDs; rubric schema defined in `CriticRubric`; decision-engine dimensions (option diversity, constraint satisfaction, recommendation justification, trade-off honesty) planned |

---

## Key design decisions

**LangGraph for orchestration** — Native hub-and-spoke topology, built-in state persistence via SQLite checkpointer, `interrupt()` for HITL, and conditional edges for the critic revision loop. No custom loop management.

**Problem type classification gates the graph** — The Solution Architect classifies the BRD as `greenfield | migration | integration | poc | enhancement` before any design work. This single field controls whether the PoC Planner runs and how the final output is sized.

**Dual model strategy** — `gpt-5.4` for Orchestrator, Solution Architect, and Critic (judgment-heavy). `gpt-5.4-mini` for Schedule Estimator, PoC Planner, Tech Stack Recommender (structured output from clear inputs).

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
