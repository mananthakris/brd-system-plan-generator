"""Generate BRDMetadata from classified sections using GPT-4o-mini."""
from __future__ import annotations

import json

from langchain_openai import ChatOpenAI

from config import settings
from schemas.models import BRDMetadata, ComplexityLevel, DocType, ProblemType


_SYSTEM_PROMPT = """\
You are a technical program manager. Analyse the document sections and return a JSON object with these fields:

{
  "doc_type":     one of ["brd","prd","rfc","adr","other"],
  "domain":       short domain label (e.g. "energy_compliance", "data_pipeline", "api_integration"),
  "complexity":   one of ["low","medium","high"],
  "problem_type": one of ["greenfield","migration","integration","poc","enhancement"] or null,
  "author":       string or null,
  "created_date": ISO date string or null,
  "version":      string or null,
  "tags":         array of up to 6 short keyword strings
}

Complexity guide:
  low    — single-service change, clear requirements, <6 weeks
  medium — multi-service, some ambiguity, 6-16 weeks
  high   — cross-domain, significant unknowns, >16 weeks or regulatory implications

Return ONLY the JSON object, no commentary.
"""


def tag_metadata(sections: list, title: str = "") -> BRDMetadata:
    """Derive BRDMetadata from a list of BRDSection objects."""
    llm = ChatOpenAI(
        model=settings.fast_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )

    sections_text = "\n\n".join(
        f"[{s.section_type.upper()}] {s.title}\n{s.content}"
        for s in sections
    )
    user_content = f"Title: {title}\n\n{sections_text}" if title else sections_text

    response = llm.invoke([
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ])

    raw = _extract_json(response.content)

    return BRDMetadata(
        doc_type=DocType(raw.get("doc_type", "other")),
        domain=raw.get("domain", "unknown"),
        complexity=ComplexityLevel(raw.get("complexity", "medium")),
        problem_type=ProblemType(raw["problem_type"]) if raw.get("problem_type") else None,
        author=raw.get("author"),
        created_date=raw.get("created_date"),
        version=raw.get("version"),
        tags=raw.get("tags", []),
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Metadata tagger returned invalid JSON: {exc}") from exc
