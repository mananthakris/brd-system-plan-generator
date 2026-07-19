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
RAG_SOURCES_DIR = Path(__file__).parent.parent / "rag" / "sources"

# Agents whose rubric asks the judge to verify "reuses Arbor's existing services" —
# these need the actual stack doc in context, or the judge is just guessing.
_STACK_GROUNDED_AGENTS = {"tech_stack_recommender", "solution_architect"}
_ARBOR_STACK_CONTEXT = (RAG_SOURCES_DIR / "current_tools_and_stack.md").read_text()
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
        "The agent MUST classify problem_type as exactly one of these 6 fixed categories — there is "
        "no 'compliance' or 'regulatory' category, so a compliance-driven BRD is correctly classified "
        "as whichever of these 6 best fits, and that is NOT a misclassification: "
        "greenfield (net-new platform, nothing existing to build on), "
        "new_feature (first-time capability on an existing platform), "
        "migration (moving between technologies/stores), "
        "integration (connecting existing systems via APIs/events), "
        "poc (explicitly time-boxed spike, not production-ready), "
        "enhancement (improving a capability that is already shipped and working). "
        "Check: (1) the chosen category is a defensible fit among these 6 given the BRD's own framing "
        "of what already exists vs. what is being built for the first time — do not penalize the "
        "classification just because a more specific label (e.g. 'compliance remediation') would also "
        "describe the BRD; (2) options are genuinely different in their critical-path architecture — "
        "if a hard latency/SLA constraint forces the same processing model everywhere, the options must "
        "still diverge on deployment unit AND data pattern, not just differ in an optional background/admin "
        "workflow while sharing an identical request-time design; "
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
    # Golden BRDs run ≤ ~5.4K chars and agent outputs run up to ~14K chars (plan_generator,
    # solution_architect, schedule_estimator all regularly exceed the old 2500-char cap) —
    # a flat 2500-char truncation was silently hiding the Functional Requirements section
    # for 2 of 4 BRDs and most of every verbose agent's output from the judge, which then
    # penalized the agent for "omitting" or "truncating" content it was never shown.
    brd_text = (input or {}).get("brd_text", "")[:8000]
    output_str = json.dumps(output, default=str)[:16000] if output else "empty"
    rubric = _AGENT_RUBRIC.get(agent_name, "Score on specificity, completeness, and relevance to the BRD.")

    stack_context = (
        f"Arbor Risk's actual existing tech stack (ground truth — do not guess; anything listed "
        f"here already exists and reusing it is NOT introducing a new service):\n{_ARBOR_STACK_CONTEXT}\n\n"
        if agent_name in _STACK_GROUNDED_AGENTS else ""
    )

    prompt = (
        f"You are evaluating the '{agent_name}' agent in a BRD-to-engineering-plan pipeline.\n\n"
        f"Rubric: {rubric}\n\n"
        f"{stack_context}"
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
# Local score snapshot — pulls ALL evaluator results (including the LLM-judge
# llm_quality score + explanation) out of the RanExperiment so they can be
# diffed from the terminal instead of read off the Phoenix UI.
# ---------------------------------------------------------------------------

def _extract_examples(ran_experiment: dict, examples_list: list) -> list[dict]:
    """One row per (example × evaluator): agent, BRD, evaluator name, score, explanation."""
    example_by_id = {ex["id"]: ex for ex in examples_list}
    example_id_by_run_id = {
        run["id"]: run["dataset_example_id"] for run in ran_experiment["task_runs"]
    }

    rows = []
    for ev_run in ran_experiment["evaluation_runs"]:
        example_id = example_id_by_run_id.get(ev_run.experiment_run_id)
        example = example_by_id.get(example_id)
        if example is None:
            continue
        inp = example.get("input") or {}
        result = ev_run.result or {}
        if isinstance(result, list):
            result = result[0] if result else {}
        # Our evaluators return a 2-tuple (score, text). Phoenix's experiment runner
        # maps a 2-tuple to (score, label), not (score, explanation) — so the judge's
        # reasoning actually lands in "label". Prefer "explanation" if ever present,
        # fall back to "label" so the real text isn't silently dropped as None.
        rows.append({
            "agent_name": inp.get("agent_name", "unknown"),
            "brd_filename": inp.get("brd_filename", "unknown"),
            "evaluator": ev_run.name,
            "score": result.get("score"),
            "explanation": result.get("explanation") or result.get("label"),
        })
    return rows


def _aggregate_scores(example_rows: list[dict]) -> dict[str, dict[str, float]]:
    """Average each evaluator's score per agent across all BRDs."""
    scores_by_agent: dict[str, dict[str, list[float]]] = {}
    for row in example_rows:
        if row["score"] is None:
            continue
        agent_scores = scores_by_agent.setdefault(row["agent_name"], {})
        agent_scores.setdefault(row["evaluator"], []).append(row["score"])
    return {
        agent: {ev: round(sum(vals) / len(vals), 4) for ev, vals in evals.items()}
        for agent, evals in scores_by_agent.items()
    }


def _save_local_snapshot(
    ran_experiment: dict, examples_list: list, experiment_name: str
) -> Path:
    """Save a full score snapshot (incl. llm_quality + judge explanations) to evals/results/."""
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    example_rows = _extract_examples(ran_experiment, examples_list)
    snapshot = {
        "experiment_name": experiment_name,
        "timestamp": datetime.datetime.now().isoformat(),
        "prompt_versions": get_all_versions(),
        "scores": _aggregate_scores(example_rows),
        "examples": example_rows,
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

    prompt_versions = get_all_versions()
    version_tag = " | ".join(f"{a}@{v}" for a, v in sorted(prompt_versions.items()))

    print(f"Running LLM-judge experiment with model '{settings.fast_model}'...")
    print("This makes one LLM call per example → ~20 calls total.\n")

    ran_experiment = client.experiments.run_experiment(
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

    print("\nSaving local snapshot (critic_score, output_completeness, llm_quality + judge explanations)...")
    snapshot_path = _save_local_snapshot(ran_experiment, examples_list, "golden-brd-llm-judge")
    print(f"Snapshot saved → {snapshot_path}")

    print(f"\nView results: {PHOENIX_URL} → Datasets & Experiments → {DATASET_NAME} → Experiments tab")
    print("Each agent × BRD row shows critic_score, completeness, and llm_quality scores.")
    print("\nImprovement cycle:")
    print("  1. Compare in the terminal: venv/bin/python -m evals.compare_experiments --latest")
    print("     (add --explanations to print judge reasoning per example, no screenshots needed)")
    print("  2. Edit prompt in prompts/registry.py (or the agent file) and bump the version")
    print("  3. Re-run: venv/bin/python -m evals.run_golden_brds && venv/bin/python -m evals.run_experiments")


if __name__ == "__main__":
    main()
