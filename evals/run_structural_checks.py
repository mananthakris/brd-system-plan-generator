"""Run deterministic structural checks against all agent outputs from a pipeline run.

Usage:
    python -m evals.run_structural_checks

Requires:
    - evals/results/golden_brd_run.json to exist (run run_golden_brds.py first)
    - Phoenix running at http://localhost:6006 to log results back as evaluations

Results are printed to stdout and optionally logged to Phoenix as span evaluations.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from rich.console import Console
from rich.table import Table

from evals.structural import CHECKS_BY_AGENT

console = Console()
RESULTS_DIR = Path(__file__).parent / "results"


def run_checks_for_agent(agent_name: str, output: dict) -> list[dict]:
    checks = CHECKS_BY_AGENT.get(agent_name, [])
    results = []
    for check_fn in checks:
        result = check_fn(output)
        results.append({
            "name": result.name,
            "passed": result.passed,
            "score": result.score,
            "evidence": result.evidence,
        })
    return results


def print_results_table(all_results: list[dict]) -> None:
    table = Table(title="Structural Check Results", show_lines=True)
    table.add_column("Agent", style="cyan")
    table.add_column("Check", style="white")
    table.add_column("Pass", justify="center")
    table.add_column("Evidence", style="dim")

    for row in all_results:
        passed_str = "[green]✓[/green]" if row["passed"] else "[red]✗[/red]"
        table.add_row(row["agent_name"], row["check_name"], passed_str, row["evidence"])

    console.print(table)

    # Summary
    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    pct = passed / total * 100 if total > 0 else 0
    color = "green" if pct >= 80 else "yellow" if pct >= 60 else "red"
    console.print(f"\n[{color}]Passed: {passed}/{total} ({pct:.0f}%)[/{color}]")


def main() -> None:
    # Load the most recent golden BRD run results to get brd_ids
    run_file = RESULTS_DIR / "golden_brd_run.json"
    if not run_file.exists():
        console.print("[red]No golden_brd_run.json found. Run: python -m evals.run_golden_brds[/red]")
        return

    with open(run_file) as f:
        run_results = json.load(f)

    # Run the agents in isolation against each golden BRD to get fresh outputs
    from rag.seed import seed
    from rag.pipeline import RAGPipeline
    from ingestion.pipeline import ingest
    from agents.planning.plan_generator import PlanGeneratorAgent
    from agents.planning.schedule_estimator import ScheduleEstimatorAgent
    from agents.design.solution_architect import SolutionArchitectAgent
    from agents.design.tech_stack_recommender import TechStackRecommenderAgent
    from agents.critic import CriticAgent
    from agents.output.formatter import OutputFormatterAgent

    # Disable Phoenix tracing for isolated checks
    os.environ["PHOENIX_TRACING"] = "0"

    seed()
    rag = RAGPipeline()

    golden_brd_files = [
        "brd_adverse_action_reason_codes.md",
        "brd_application_fraud_scoring.md",
        "brd_first_party_fraud_case_management.md",
        "brd_synthetic_identity_detection.md",
    ]
    sources_dir = Path(__file__).parent.parent / "rag" / "sources"

    all_check_results = []

    for brd_file in golden_brd_files:
        brd_path = sources_dir / brd_file
        if not brd_path.exists():
            continue

        console.print(f"\n[bold]BRD:[/bold] {brd_file}")
        brd_input = ingest(source=brd_path)
        brd_dict = brd_input.model_dump(mode="json")

        # Run each agent in isolation and check its output
        agent_runs: list[tuple[str, dict, dict | None]] = []

        plan_out = PlanGeneratorAgent(rag).run(brd_dict)
        agent_runs.append(("plan_generator", plan_out, None))

        arch_out = SolutionArchitectAgent(rag).run(brd_dict)
        agent_runs.append(("solution_architect", arch_out, None))

        tech_out = TechStackRecommenderAgent(rag).run(brd_dict, architect_output=arch_out)
        agent_runs.append(("tech_stack_recommender", tech_out, None))

        sched_out = ScheduleEstimatorAgent().run(
            brd_input=brd_dict, plan_output=plan_out, tech_stack_output=tech_out
        )
        agent_runs.append(("schedule_estimator", sched_out, None))

        critic_out = CriticAgent().run(
            brd_input=brd_dict,
            plan_output=plan_out,
            architect_output=arch_out,
            tech_stack_output=tech_out,
        )
        agent_runs.append(("critic", critic_out, None))

        formatter_out = OutputFormatterAgent().run(
            brd_input=brd_dict,
            plan_output=plan_out,
            architect_output=arch_out,
            tech_stack_output=tech_out,
            schedule_output=sched_out,
            critic_output=critic_out,
            revision_count=0,
        )
        agent_runs.append(("output_formatter", formatter_out, None))

        for agent_name, output, _ in agent_runs:
            check_results = run_checks_for_agent(agent_name, output)
            for r in check_results:
                all_check_results.append({
                    "agent_name": agent_name,
                    "brd_file": brd_file,
                    "check_name": r["name"],
                    "passed": r["passed"],
                    "score": r["score"],
                    "evidence": r["evidence"],
                })

    print_results_table(all_check_results)

    # Save results
    out_file = RESULTS_DIR / "structural_check_results.json"
    out_file.parent.mkdir(exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(all_check_results, f, indent=2)
    console.print(f"\nResults saved to {out_file}")


if __name__ == "__main__":
    main()
