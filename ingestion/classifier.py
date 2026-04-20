"""Classify parsed document text into typed BRD sections using GPT-4o-mini."""
from __future__ import annotations

import json

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import settings
from schemas.models import BRDSection


_SECTION_TYPES = [
    "objective",
    "background",
    "functional_requirements",
    "non_functional_requirements",
    "constraints",
    "stakeholders",
    "success_criteria",
    "timeline",
    "budget",
    "risks",
    "out_of_scope",
    "open_questions",
]

_SYSTEM_PROMPT = """\
You are a technical document analyst. Split the provided document text into sections and classify each one.

Return a JSON array. Each element must have:
  - "section_type": one of {section_types}
  - "title": a short human-readable title (≤10 words)
  - "content": the full text of that section

Rules:
- Every meaningful block of text must appear in exactly one section.
- If the document has explicit headings, use them as section boundaries.
- If no explicit heading exists, infer section boundaries from content semantics.
- Merge very short fragments (< 3 sentences) into the nearest relevant section.
- Return ONLY the JSON array, no commentary.
""".format(section_types=json.dumps(_SECTION_TYPES))


class _ClassifiedSection(BaseModel):
    section_type: str
    title: str
    content: str


def classify_sections(raw_text: str) -> list[BRDSection]:
    """Return typed BRDSection list from raw document text."""
    llm = ChatOpenAI(
        model=settings.fast_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )

    response = llm.invoke([
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": raw_text},
    ])

    raw_json = _extract_json(response.content)
    sections = []
    for item in raw_json:
        try:
            parsed = _ClassifiedSection(**item)
            sections.append(BRDSection(
                section_type=parsed.section_type if parsed.section_type in _SECTION_TYPES else "other",
                title=parsed.title,
                content=parsed.content,
            ))
        except Exception:
            continue

    return sections


def _extract_json(text: str) -> list[dict]:
    """Strip markdown fences and parse JSON."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Section classifier returned invalid JSON: {exc}") from exc
