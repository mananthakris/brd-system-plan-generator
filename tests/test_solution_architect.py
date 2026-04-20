"""Smoke test for the Solution Architect agent.

Run with:
    python -m tests.test_solution_architect

Tests the agent in isolation — no LangGraph graph, no other agents.
Requires OPENAI_API_KEY in .env and a seeded Chroma collection.
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.json import JSON

console = Console()


def main() -> None:
    from ingestion.pipeline import ingest
    from rag.pipeline import RAGPipeline
    from rag.seed import seed as seed_rag
    from agents.design.solution_architect import SolutionArchitectAgent
    from guardrails.checks import validate_agent_output, GuardrailError
    from schemas.models import AgentOutput

    # ------------------------------------------------------------------
    # 1. Seed RAG
    # ------------------------------------------------------------------
    console.print(Panel("[bold]Step 1: Seeding RAG[/bold]", style="blue"))
    rag = seed_rag()

    # ------------------------------------------------------------------
    # 2. Ingest the sample BRD
    # ------------------------------------------------------------------
    console.print(Panel("[bold]Step 2: Ingesting BRD[/bold]", style="blue"))
    brd_path = Path(__file__).parent.parent / "rag/sources/brd_penalty_forecasting_engine.md"
    brd_input = ingest(
        source=str(brd_path),
        title="Automated Carbon Penalty Forecasting Engine",
    )
    console.print(f"  problem_type (tagger): [cyan]{brd_input.metadata.problem_type}[/cyan]")
    console.print(f"  complexity:            [cyan]{brd_input.metadata.complexity}[/cyan]")
    console.print(f"  sections:              {len(brd_input.sections)}")

    # ------------------------------------------------------------------
    # 3. Run Solution Architect
    # ------------------------------------------------------------------
    console.print(Panel("[bold]Step 3: Running Solution Architect[/bold]", style="blue"))
    agent = SolutionArchitectAgent(rag)
    output_dict = agent.run(brd_input.model_dump(mode="json"))

    # ------------------------------------------------------------------
    # 4. Validate output schema
    # ------------------------------------------------------------------
    console.print(Panel("[bold]Step 4: Validating output[/bold]", style="blue"))
    try:
        output = AgentOutput.model_validate(output_dict)
        validate_agent_output(output)
        console.print("  [green]✓ Schema valid[/green]")
        console.print("  [green]✓ Guardrails passed[/green]")
    except GuardrailError as exc:
        console.print(f"  [red]✗ Guardrail failed: {exc}[/red]")
        raise
    except Exception as exc:
        console.print(f"  [red]✗ Schema validation failed: {exc}[/red]")
        raise

    # ------------------------------------------------------------------
    # 5. Print results
    # ------------------------------------------------------------------
    content = output_dict.get("content", {})

    console.print(Panel("[bold green]Solution Architect Output[/bold green]"))
    console.print(f"\n[bold]Problem type:[/bold] [yellow]{content.get('problem_type')}[/yellow]")

    console.print("\n[bold]High-level components:[/bold]")
    for c in content.get("high_level_components", []):
        console.print(f"  • {c}")

    console.print(f"\n[bold]Data flow:[/bold]\n{content.get('data_flow')}")

    console.print("\n[bold]Integration points:[/bold]")
    for p in content.get("integration_points", []):
        console.print(f"  • {p}")

    console.print("\n[bold]Constraints addressed:[/bold]")
    for ca in content.get("constraints_addressed", []):
        console.print(f"  • {ca}")

    console.print(f"\n[bold]Tokens used:[/bold] {output_dict.get('tokens_used')}")
    console.print(f"[bold]RAG chunks retrieved:[/bold] {len((output_dict.get('rag_context') or {}).get('retrieved_chunks', []))}")

    console.print("\n[dim]Full output JSON:[/dim]")
    # Truncate raw_content in brd_input for readability
    printable = {k: v for k, v in output_dict.items() if k != "rag_context"}
    console.print(JSON(json.dumps(printable, indent=2, default=str)))


if __name__ == "__main__":
    main()
