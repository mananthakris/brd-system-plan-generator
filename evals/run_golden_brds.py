"""Run all 4 golden BRDs through the full pipeline so traces appear in Phoenix
and a dataset is created/updated for the evaluation cycle.

Usage:
    1. Start Phoenix first (keep it running):
           venv/bin/python -m phoenix.server.main serve
    2. Then in a separate terminal run this script:
           venv/bin/python -m evals.run_golden_brds

Traces appear at http://localhost:6006 under project "brd-planner".
A dataset named "golden_brd_evals" is created/updated automatically —
Phoenix's "Add to Dataset" UI only works for LLM-kind spans, not AGENT spans,
so dataset creation is done programmatically here.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

GOLDEN_BRDS = [
    "brd_adverse_action_reason_codes.md",
    "brd_application_fraud_scoring.md",
    "brd_first_party_fraud_case_management.md",
    "brd_synthetic_identity_detection.md",
]

# Agents whose outputs are captured as individual dataset examples.
# Each BRD × agent = one example → 4 BRDs × 5 agents = 20 examples per run.
_AGENT_OUTPUT_KEYS = {
    "plan_generator": "plan_output",
    "solution_architect": "architect_output",
    "tech_stack_recommender": "tech_stack_output",
    "schedule_estimator": "schedule_output",
    "critic": "critic_output",
}

RAG_SOURCES_DIR = Path(__file__).parent.parent / "rag" / "sources"
OUTPUT_DIR = Path(__file__).parent / "results"
DATASET_NAME = "golden_brd_evals"
PHOENIX_URL = "http://localhost:6006"


def _check_phoenix_running() -> None:
    try:
        urllib.request.urlopen(PHOENIX_URL, timeout=3)
    except Exception:
        print(
            f"ERROR: Phoenix is not running at {PHOENIX_URL}.\n"
            "Start it first with:\n"
            "    venv/bin/python -m phoenix.server.main serve\n"
            "Then re-run this script."
        )
        sys.exit(1)


def _build_dataset_examples(brd_runs: list[dict]) -> list[dict]:
    """
    Build one dataset example per agent per BRD run.
    input  = agent name + BRD context (what the agent received)
    output = agent's structured content dict (what the agent produced)
    """
    examples = []
    for run in brd_runs:
        brd_text = run["brd_text"]
        for agent_name, output_key in _AGENT_OUTPUT_KEYS.items():
            agent_output = run["state"].get(output_key) or {}
            content = agent_output.get("content") or {}
            if not content:
                continue
            examples.append({
                "input": {
                    "agent_name": agent_name,
                    "brd_filename": run["brd_filename"],
                    "brd_title": run["brd_title"],
                    "brd_text": brd_text[:5000],
                },
                "output": content,
                "metadata": {
                    "brd_id": run["brd_id"],
                    "critic_score": run["critic_score"],
                    "revision_count": run["revision_count"],
                },
            })
    return examples


def _upsert_phoenix_dataset(examples: list[dict]) -> None:
    """
    Create the dataset on first run; add a new version on subsequent runs.
    Phoenix datasets are versioned — add_examples_to_dataset always creates
    the latest version, so run_phoenix_evals.py always evaluates the freshest data.
    """
    from phoenix.client import Client
    client = Client()

    try:
        client.datasets.get_dataset(dataset=DATASET_NAME)
        # Dataset exists — add a new version with the fresh examples.
        dataset = client.datasets.add_examples_to_dataset(
            dataset=DATASET_NAME,
            examples=examples,
        )
        print(f"Dataset '{DATASET_NAME}' updated: {len(examples)} examples added (new version).")
    except Exception:
        # Dataset does not exist — create it.
        try:
            dataset = client.datasets.create_dataset(
                name=DATASET_NAME,
                examples=examples,
                dataset_description=(
                    "Golden fraud-domain BRDs — 4 BRDs × 5 agents = 20 examples per run. "
                    "Used by run_phoenix_evals.py for LLM-as-Judge scoring."
                ),
            )
            print(f"Dataset '{DATASET_NAME}' created: {len(examples)} examples.")
        except Exception as exc:
            print(f"Warning: could not create/update Phoenix dataset: {exc}")
            return

    print(f"View dataset: {PHOENIX_URL} → Datasets & Experiments → {DATASET_NAME}")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    _check_phoenix_running()
    print(f"Phoenix UI: {PHOENIX_URL}\n")

    from rag.seed import seed
    from rag.pipeline import RAGPipeline
    from ingestion.pipeline import ingest
    from agents.orchestrator import build_graph

    print("Seeding RAG...")
    seed()

    rag = RAGPipeline()
    graph = build_graph(rag=rag)

    summary_rows = []
    brd_runs = []

    for brd_filename in GOLDEN_BRDS:
        brd_path = RAG_SOURCES_DIR / brd_filename
        if not brd_path.exists():
            print(f"  SKIP {brd_filename} (not found)")
            continue

        print(f"Running: {brd_filename}")
        brd_input = ingest(source=brd_path)
        brd_text = brd_path.read_text()

        config = {"configurable": {"thread_id": f"eval-{brd_input.id}"}}
        state = graph.invoke(
            {"brd_input": brd_input.model_dump(mode="json")},
            config=config,
        )

        critic_score = (state.get("critic_output") or {}).get("content", {}).get("overall_score")
        revision_count = state.get("revision_count", 0)

        summary_rows.append({
            "brd_id": brd_input.id,
            "brd_filename": brd_filename,
            "brd_title": brd_input.title,
            "critic_score": critic_score,
            "revision_count": revision_count,
        })

        brd_runs.append({
            "brd_id": brd_input.id,
            "brd_filename": brd_filename,
            "brd_title": brd_input.title,
            "brd_text": brd_text,
            "critic_score": critic_score,
            "revision_count": revision_count,
            "state": state,
        })

        print(f"  critic_score={critic_score}, revisions={revision_count}")

    output_file = OUTPUT_DIR / "golden_brd_run.json"
    output_file.write_text(json.dumps(summary_rows, indent=2))
    print(f"\nSummary saved to {output_file}")

    print("\nBuilding Phoenix dataset...")
    examples = _build_dataset_examples(brd_runs)
    _upsert_phoenix_dataset(examples)

    print("\nNext steps:")
    print("  venv/bin/python -m evals.run_structural_checks")
    print("  venv/bin/python -m evals.run_phoenix_evals")


if __name__ == "__main__":
    main()
