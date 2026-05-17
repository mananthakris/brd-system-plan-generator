"""Run a Phoenix experiment on the golden_brd_evals dataset using LLM-as-judge evaluators.

This is the correct way to see evaluation results in the Phoenix UI under
Datasets & Experiments → golden_brd_evals → Experiments tab.

Usage:
    1. Start Phoenix:        venv/bin/python -m phoenix.server.main serve
    2. Generate traces:      venv/bin/python -m evals.run_golden_brds
    3. Run this experiment:  venv/bin/python -m evals.run_experiments

Results appear in Phoenix UI → Datasets & Experiments → golden_brd_evals → Experiments.
Each experiment run is versioned, so you can compare scores before/after a prompt change.

Improvement cycle:
    1. Run experiment → identify low-scoring agent in the Experiments tab
    2. Open a failing example → read the LLM judge explanation
    3. Edit the system prompt in agents/<group>/<agent>.py
    4. Re-run golden_brds + run_experiments → compare scores across experiment versions
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

from phoenix.client import Client

from config import settings
from prompts.registry import get_all_versions

DATASET_NAME = "golden_brd_evals"
PHOENIX_URL = "http://localhost:6006"
RESULTS_DIR = Path(__file__).parent / "results"


def _check_phoenix_running() -> None:
    try:
        urllib.request.urlopen(PHOENIX_URL, timeout=3)
    except Exception:
        print(
            f"ERROR: Phoenix is not running at {PHOENIX_URL}.\n"
            "Start it with: venv/bin/python -m phoenix.server.main serve"
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Task — passthrough: evaluate outputs already stored in the dataset.
# No pipeline re-run needed; the golden BRD run already produced the outputs.
# ---------------------------------------------------------------------------

def task(example: Any) -> Any:
    """Return the stored agent output from the dataset example."""
    return example.output


# ---------------------------------------------------------------------------
# Rule-based evaluators (free, no LLM calls)
# ---------------------------------------------------------------------------

def critic_score(metadata: Any) -> tuple[float, str]:
    """Normalised overall_score from the critic agent (0–1). Stored in example metadata."""
    score = (metadata or {}).get("critic_score")
    if score is None:
        return 0.5, "no critic score in metadata"
    normalised = min(float(score) / 10.0, 1.0)
    label = "pass" if normalised >= 0.7 else "fail"
    return normalised, f"critic_score={score} → {label}"


def output_completeness(output: Any) -> tuple[float, str]:
    """Fraction of non-empty fields in the agent output content dict."""
    if not output or not isinstance(output, dict):
        return 0.0, "output is empty or not a dict"
    values = list(output.values())
    non_empty = sum(1 for v in values if v not in (None, "", [], {}))
    score = non_empty / len(values) if values else 0.0
    return score, f"{non_empty}/{len(values)} fields populated"


# ---------------------------------------------------------------------------
# LLM-as-Judge evaluator (uses FAST_MODEL from .env)
# ---------------------------------------------------------------------------

# Agent-specific rubric hints injected into the judge prompt.
_AGENT_RUBRIC: dict[str, str] = {
    "plan_generator": (
        "Check: (1) every major BRD requirement maps to a phase deliverable, "
        "(2) phases are in logical order, (3) no out-of-scope items are included."
    ),
    "solution_architect": (
        "Check: (1) problem_type classification matches the BRD, "
        "(2) options are genuinely different architectural approaches (not just config variants), "
        "(3) components are named specifically using services from the RAG context — not generic terms "
        "like 'message queue' or 'database' (e.g. should say 'Amazon SQS', 'Aurora Postgres', not just 'queue')."
    ),
    "tech_stack_recommender": (
        "Check: (1) recommended option primarily uses Arbor's existing services rather than introducing new ones, "
        "(2) all explicit BRD constraints (AWS-only, latency SLAs, etc.) are respected."
    ),
    "schedule_estimator": (
        "Check: (1) every risk has a specific, actionable mitigation (not just 'monitor'), "
        "(2) every assumption references specific BRD details (team size, named services, explicit constraints)."
    ),
    "critic": (
        "Check: (1) every feedback point names a specific phase, component, or deliverable, "
        "(2) revision notes tell the generator exactly what to change, not vague advice like 'add more detail'."
    ),
}


def llm_quality(input: Any, output: Any) -> tuple[float, str]:
    """LLM-as-judge: scores agent output quality against the BRD using FAST_MODEL."""
    import openai
    client = openai.OpenAI(api_key=settings.openai_api_key)

    agent_name = (input or {}).get("agent_name", "unknown")
    brd_text = (input or {}).get("brd_text", "")[:2500]
    output_str = json.dumps(output, default=str)[:2500] if output else "empty"
    rubric = _AGENT_RUBRIC.get(agent_name, "Score on specificity, completeness, and relevance to the BRD.")

    prompt = (
        f"You are evaluating the '{agent_name}' agent in a BRD-to-engineering-plan pipeline.\n\n"
        f"Rubric: {rubric}\n\n"
        f"BRD excerpt:\n{brd_text}\n\n"
        f"Agent output:\n{output_str}\n\n"
        f"Score 0.0–1.0 based on the rubric above. "
        f"Respond ONLY as: <score> | <one sentence citing the specific strength or failure>\n"
        f"Example: 0.8 | Plan maps all BRD requirements to specific deliverables with SQS and Aurora Postgres named."
    )

    try:
        resp = client.chat.completions.create(
            model=settings.fast_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
        score_str, explanation = text.split("|", 1)
        return float(score_str.strip()), explanation.strip()
    except Exception as exc:
        return 0.5, f"judge error: {exc}"


# ---------------------------------------------------------------------------
# Local score snapshot (rule-based only, no LLM calls — used by compare_experiments.py)
# ---------------------------------------------------------------------------

def _compute_local_scores(examples: list) -> dict[str, dict[str, float]]:
    """Average rule-based scores per agent across all examples (no LLM calls)."""
    scores_by_agent: dict[str, dict[str, list[float]]] = {}
    for example in examples:
        inp = getattr(example, "input", None) or {}
        out = getattr(example, "output", None)
        meta = getattr(example, "metadata", None)
        agent_name = inp.get("agent_name", "unknown") if isinstance(inp, dict) else "unknown"
        cs = critic_score(meta)[0]
        oc = output_completeness(out)[0]
        if agent_name not in scores_by_agent:
            scores_by_agent[agent_name] = {"critic_score": [], "output_completeness": []}
        scores_by_agent[agent_name]["critic_score"].append(cs)
        scores_by_agent[agent_name]["output_completeness"].append(oc)
    return {
        agent: {k: round(sum(v) / len(v), 4) for k, v in evals.items()}
        for agent, evals in scores_by_agent.items()
    }


def _save_local_snapshot(scores: dict, experiment_name: str) -> Path:
    """Save a score snapshot to evals/results/ tagged with the current prompt versions."""
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot = {
        "experiment_name": experiment_name,
        "timestamp": datetime.datetime.now().isoformat(),
        "prompt_versions": get_all_versions(),
        "note": (
            "Rule-based scores (critic_score, output_completeness) averaged per agent across all BRDs. "
            "LLM quality scores are in the Phoenix UI Experiments tab."
        ),
        "scores": scores,
    }
    path = RESULTS_DIR / f"experiment_{timestamp}.json"
    path.write_text(json.dumps(snapshot, indent=2))
    return path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _check_phoenix_running()
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key

    client = Client()

    print(f"Loading dataset '{DATASET_NAME}'...")
    try:
        dataset = client.datasets.get_dataset(dataset=DATASET_NAME)
    except Exception as exc:
        print(f"ERROR: could not load dataset '{DATASET_NAME}': {exc}")
        print("Run: venv/bin/python -m evals.run_golden_brds")
        sys.exit(1)

    examples_list = list(dataset)
    example_count = len(examples_list)
    print(f"Loaded {example_count} examples (4 BRDs × 5 agents).")

    print("Computing local rule-based scores (no LLM calls)...")
    local_scores = _compute_local_scores(examples_list)
    snapshot_path = _save_local_snapshot(local_scores, "golden-brd-llm-judge")
    print(f"Local snapshot saved → {snapshot_path}")
    print(f"  (use venv/bin/python -m evals.compare_experiments to diff two snapshots)\n")

    prompt_versions = get_all_versions()
    version_tag = " | ".join(f"{a}@{v}" for a, v in sorted(prompt_versions.items()))

    print(f"Running LLM-judge experiment with model '{settings.fast_model}'...")
    print("This makes one LLM call per example → ~20 calls total.\n")

    client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators=[critic_score, output_completeness, llm_quality],
        experiment_name="golden-brd-llm-judge",
        experiment_description=(
            f"LLM-as-judge scoring of all 5 agent outputs across 4 golden BRDs. "
            f"Prompt versions: {version_tag}. "
            f"Re-run after editing a prompt to compare scores across experiment versions."
        ),
    )

    print(f"\nView results: {PHOENIX_URL} → Datasets & Experiments → {DATASET_NAME} → Experiments tab")
    print("Each agent × BRD row shows critic_score, completeness, and llm_quality scores.")
    print("\nImprovement cycle:")
    print("  1. Find low llm_quality rows → read the judge explanation")
    print("  2. Edit prompt in prompts/registry.py and bump the version")
    print("  3. Re-run: venv/bin/python -m evals.run_golden_brds && venv/bin/python -m evals.run_experiments")
    print("  4. Compare: venv/bin/python -m evals.compare_experiments --baseline <old.json> --candidate <new.json>")


if __name__ == "__main__":
    main()
