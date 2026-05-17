"""Populate Chroma with all Arbor Risk knowledge base documents."""
from __future__ import annotations

from pathlib import Path

from rich.console import Console

from rag.pipeline import RAGPipeline

console = Console()
SOURCES_DIR = Path(__file__).parent / "sources"


def seed(reset: bool = False) -> RAGPipeline:
    rag = RAGPipeline()

    if reset:
        console.print("[yellow]Resetting collection...[/yellow]")
        import chromadb
        from config import settings
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        try:
            client.delete_collection("arbor_knowledge")
        except Exception:
            pass
        rag = RAGPipeline()

    before = rag.count()
    console.print(f"[dim]Collection has {before} chunks before seeding[/dim]")

    console.print(f"\n[bold]Seeding from {SOURCES_DIR}[/bold]")
    added = rag.seed_from_directory(SOURCES_DIR)

    after = rag.count()
    console.print(f"\n[green]✓ Seeded {added} new chunks. Collection total: {after}[/green]")
    return rag


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild collection")
    args = parser.parse_args()

    seed(reset=args.reset)
