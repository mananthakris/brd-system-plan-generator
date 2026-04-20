"""Compose parser → classifier → tagger into a single ingestion call."""
from __future__ import annotations

import uuid
from pathlib import Path

from schemas.models import BRDInput
from .parser import parse_document, parse_text
from .classifier import classify_sections
from .tagger import tag_metadata


def ingest(
    source: str | Path | None = None,
    raw_text: str | None = None,
    title: str = "",
    context_docs: list[str] | None = None,
) -> BRDInput:
    """
    Parse, classify, and tag a BRD/PRD document.

    Pass either `source` (file path) or `raw_text`.
    """
    if source is not None:
        text = parse_document(source)
        if not title:
            title = Path(source).stem.replace("_", " ").title()
    elif raw_text is not None:
        text = parse_text(raw_text)
    else:
        raise ValueError("Provide either source path or raw_text")

    sections = classify_sections(text)
    metadata = tag_metadata(sections, title=title)

    return BRDInput(
        id=str(uuid.uuid4()),
        title=title,
        raw_content=text,
        sections=sections,
        metadata=metadata,
        context_docs=context_docs or [],
    )
