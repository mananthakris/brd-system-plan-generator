"""Span diagnostic report — shows what agent spans exist in Phoenix.

Run this to verify traces were recorded correctly before running experiments.
LLM-as-judge evaluation is done via run_experiments.py, not this script.

Usage:
    venv/bin/python -m evals.run_phoenix_evals
"""
from __future__ import annotations

import os

import pandas as pd
from rich.console import Console
from rich.table import Table

from phoenix.client import Client as PhoenixClient

from config import settings

console = Console()


def get_spans_as_dataframe(project_name: str = "brd-planner") -> pd.DataFrame:
    client = PhoenixClient()
    try:
        return client.spans.get_spans_dataframe(project_name=project_name)
    except Exception as exc:
        console.print(f"[red]Failed to fetch spans from Phoenix: {exc}[/red]")
        console.print("Is Phoenix running? Start with: venv/bin/python -m phoenix.server.main serve")
        raise


def main() -> None:
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

    console.print("Fetching spans from Phoenix...")
    try:
        df = get_spans_as_dataframe()
    except Exception:
        return

    if df.empty:
        console.print("[yellow]No spans found. Run venv/bin/python -m evals.run_golden_brds first.[/yellow]")
        return

    console.print(f"Total spans: {len(df)}\n")

    # Count spans per kind and agent
    kind_col = "attributes.openinference.span.kind" if "attributes.openinference.span.kind" in df.columns else None
    name_col = "attributes.agent.name" if "attributes.agent.name" in df.columns else None

    table = Table(title="Spans by Kind", show_lines=True)
    table.add_column("Kind", style="cyan")
    table.add_column("Count", justify="right")

    if kind_col:
        for kind, count in df[kind_col].value_counts().items():
            table.add_row(str(kind), str(count))
    else:
        table.add_row("(kind column not found)", str(len(df)))
    console.print(table)

    if name_col:
        agent_table = Table(title="Agent Spans", show_lines=True)
        agent_table.add_column("Agent", style="cyan")
        agent_table.add_column("Spans", justify="right")
        agent_table.add_column("Has Input", justify="right")
        agent_table.add_column("Has Output", justify="right")

        agent_df = df[df[name_col].notna()].copy()
        for agent_name, group in agent_df.groupby(name_col):
            has_input = group["attributes.input.value"].notna().sum() if "attributes.input.value" in group else 0
            has_output = group["attributes.output.value"].notna().sum() if "attributes.output.value" in group else 0
            agent_table.add_row(str(agent_name), str(len(group)), str(has_input), str(has_output))

        console.print(agent_table)

    console.print("\n[bold]Next step:[/bold]")
    console.print("  venv/bin/python -m evals.run_experiments   ← runs LLM-as-judge, results appear in Phoenix UI")


if __name__ == "__main__":
    main()
