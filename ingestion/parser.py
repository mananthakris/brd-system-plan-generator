"""Parse BRD/PRD documents into raw text.

Supported formats: .pdf, .docx, .md, .txt
"""
from __future__ import annotations

import re
from pathlib import Path


def parse_document(source: str | Path) -> str:
    """Return the full text content of a document file."""
    path = Path(source)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(path)
    elif suffix == ".docx":
        return _parse_docx(path)
    elif suffix in (".md", ".txt", ""):
        return path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def parse_text(raw: str) -> str:
    """Accept raw text directly (no file I/O)."""
    return _clean(raw)


# ---------------------------------------------------------------------------
# Format-specific helpers
# ---------------------------------------------------------------------------

def _parse_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("pypdf required for PDF parsing: pip install pypdf") from exc

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return _clean("\n\n".join(pages))


def _parse_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ImportError("python-docx required: pip install python-docx") from exc

    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return _clean("\n\n".join(paragraphs))


def _clean(text: str) -> str:
    """Normalise whitespace while preserving paragraph breaks."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()
