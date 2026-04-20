# Developer Setup Guide

## Prerequisites

- Python 3.11+ (the project uses `list[str]` and `X | Y` union syntax; 3.9 will fail)
- An OpenAI API key with access to `gpt-4o`, `gpt-4o-mini`, and `text-embedding-3-small`

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
| `ORCHESTRATOR_MODEL` | `gpt-4o` | Swap to `gpt-4o-mini` to cut cost during dev |
| `AGENT_MODEL` | `gpt-4o` | Same |
| `CHROMA_PERSIST_DIR` | `.chroma` | Change if you want the DB elsewhere |
| `RAG_SCORE_THRESHOLD` | `0.75` | Lower to `0.5` if retrieval returns nothing |
| `MAX_REVISION_CYCLES` | `2` | Set to `0` to skip the critic revision loop |

---

## 4. Seed the RAG knowledge base

This loads the Verdant Intelligence knowledge base (architecture decisions, team skills, cloud infra, domain context, sample BRD) into ChromaDB. It is idempotent — safe to run multiple times.

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

## 7. Adding a new agent (Phase 2 pattern)

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
The GPT-4o calls in `solution_architect.py` are sequential (classify, then design) — no parallelism to cause burst. If you hit limits, set `ORCHESTRATOR_MODEL=gpt-4o-mini` in `.env` for development.

**RAG returning no results (empty `retrieved_chunks`)**
Lower `RAG_SCORE_THRESHOLD` to `0.5` in `.env` and re-run. If still empty, confirm the seed ran successfully with `python3 -m rag.seed`.

**`with_structured_output` parsing errors**
Intermittent JSON parse failures from the LLM. Re-running usually resolves it. If persistent, the model may be hitting a context limit — try shortening the BRD input or switching to `gpt-4o`.
