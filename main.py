"""Entry point: ingest a BRD and run the multi-agent pipeline."""
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.json import JSON

from config import settings
from ingestion.pipeline import ingest
from rag.pipeline import RAGPipeline
from rag.seed import seed as seed_rag
from agents.orchestrator import build_graph
from guardrails.checks import validate_brd_input, GuardrailError
from state.store import StateStore

console = Console()


def run(
    brd_source: str | None = None,
    brd_text: str | None = None,
    title: str = "",
    skip_seed: bool = False,
    session_id: str | None = None,
) -> dict:
    session_id = session_id or str(uuid.uuid4())
    store = StateStore()

    # ------------------------------------------------------------------
    # 1. Seed RAG (idempotent — Chroma upserts by ID)
    # ------------------------------------------------------------------
    if not skip_seed:
        console.print(Panel("[bold]Step 1: Seeding RAG knowledge base[/bold]", style="blue"))
        seed_rag()
    else:
        console.print("[dim]Skipping RAG seed (--skip-seed)[/dim]")

    # ------------------------------------------------------------------
    # 2. Ingest BRD
    # ------------------------------------------------------------------
    console.print(Panel("[bold]Step 2: Ingesting BRD[/bold]", style="blue"))
    try:
        brd_input = ingest(source=brd_source, raw_text=brd_text, title=title)
        console.print(f"  ✓ Parsed: [green]{brd_input.title}[/green]")
        console.print(f"  ✓ Sections: {len(brd_input.sections)}")
        console.print(f"  ✓ Problem type: {brd_input.metadata.problem_type}")
        console.print(f"  ✓ Complexity: {brd_input.metadata.complexity}")
        console.print(f"  ✓ Tags: {', '.join(brd_input.metadata.tags)}")
    except Exception as exc:
        console.print(f"[red]Ingestion failed: {exc}[/red]")
        raise

    # ------------------------------------------------------------------
    # 3. Guardrails — input validation
    # ------------------------------------------------------------------
    try:
        validate_brd_input(brd_input)
        console.print("  ✓ Guardrails passed")
    except GuardrailError as exc:
        console.print(f"[red]Guardrail blocked: {exc}[/red]")
        raise

    # ------------------------------------------------------------------
    # 4. Register session
    # ------------------------------------------------------------------
    store.create_session(session_id, brd_input.id, brd_input.title)
    console.print(f"  ✓ Session: [dim]{session_id}[/dim]")

    # ------------------------------------------------------------------
    # 5. Run LangGraph pipeline
    # ------------------------------------------------------------------
    console.print(Panel("[bold]Step 3: Running multi-agent pipeline[/bold]", style="blue"))

    graph = build_graph()
    initial_state: dict = {
        "brd_input": brd_input.model_dump(mode="json"),
        "rag_context": {},
        "plan_output": None,
        "schedule_output": None,
        "architect_output": None,
        "poc_output": None,
        "tech_stack_output": None,
        "critic_output": None,
        "engineering_plan": None,
        "revision_count": 0,
        "hitl_approved": False,
        "errors": [],
    }

    config = {"configurable": {"thread_id": session_id}}
    final_state = None

    for step in graph.stream(initial_state, config=config):
        node_name = list(step.keys())[0]
        console.print(f"  → [cyan]{node_name}[/cyan]")
        final_state = step

    # ------------------------------------------------------------------
    # 6. Extract result
    # ------------------------------------------------------------------
    # LangGraph stream yields {node_name: state_delta}; reconstruct full state
    full_state = graph.get_state(config).values
    plan = full_state.get("engineering_plan") or {}

    console.print(Panel("[bold green]Pipeline complete[/bold green]"))
    console.print(JSON(json.dumps(plan, indent=2, default=str)))

    store.update_session_status(session_id, "complete")
    return plan


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Verdant Intelligence — BRD to Engineering Plan")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--brd-file", help="Path to BRD file (.pdf, .docx, .md, .txt)")
    source_group.add_argument("--brd-text", help="Raw BRD text (inline)")
    source_group.add_argument(
        "--demo",
        action="store_true",
        help="Run with the built-in Penalty Forecasting BRD sample",
    )
    parser.add_argument("--title", default="", help="Document title override")
    parser.add_argument("--session-id", default=None, help="Resume an existing session")
    parser.add_argument("--skip-seed", action="store_true", help="Skip RAG seeding step")

    args = parser.parse_args()

    if args.demo:
        demo_path = Path(__file__).parent / "rag/sources/brd_penalty_forecasting_engine.md"
        run(brd_source=str(demo_path), title="Automated Carbon Penalty Forecasting Engine", skip_seed=args.skip_seed)
    elif args.brd_file:
        run(brd_source=args.brd_file, title=args.title, skip_seed=args.skip_seed, session_id=args.session_id)
    else:
        run(brd_text=args.brd_text, title=args.title, skip_seed=args.skip_seed, session_id=args.session_id)


if __name__ == "__main__":
    main()
