"""Deterministic structural checks for output_formatter output."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float
    evidence: str


_TIMELINE_WORDS = re.compile(r"\b(week|month|timeline|sprint)\b", re.IGNORECASE)
_BULLET_LINE = re.compile(r"^\s*[-•]", re.MULTILINE)
_HEADER_LINE = re.compile(r"^#{1,6}\s", re.MULTILINE)


def _get_summary(output: dict) -> str:
    plan = output.get("content") or {}
    return plan.get("executive_summary", "")


def check_summary_word_count(output: dict) -> CheckResult:
    summary = _get_summary(output)
    count = len(summary.split())
    passed = 150 <= count <= 300
    return CheckResult("summary_word_count", passed, float(passed),
                       f"Word count: {count} (expected 150–300)")


def check_three_paragraph_structure(output: dict) -> CheckResult:
    summary = _get_summary(output)
    paragraphs = [p.strip() for p in summary.split("\n\n") if p.strip()]
    passed = len(paragraphs) >= 3
    return CheckResult("three_paragraph_structure", passed, float(passed),
                       f"Paragraph count: {len(paragraphs)} (expected >= 3)")


def check_no_bullet_points(output: dict) -> CheckResult:
    summary = _get_summary(output)
    passed = not bool(_BULLET_LINE.search(summary))
    return CheckResult("no_bullet_points", passed, float(passed),
                       "No bullet points found" if passed else "Bullet points detected in summary")


def check_no_headers(output: dict) -> CheckResult:
    summary = _get_summary(output)
    passed = not bool(_HEADER_LINE.search(summary))
    return CheckResult("no_headers", passed, float(passed),
                       "No markdown headers found" if passed else "Markdown headers detected in summary")


def check_mentions_timeline(output: dict) -> CheckResult:
    summary = _get_summary(output)
    passed = bool(_TIMELINE_WORDS.search(summary))
    return CheckResult("mentions_timeline", passed, float(passed),
                       "Timeline reference found" if passed else "No timeline reference in summary")


def check_plan_id_present(output: dict) -> CheckResult:
    plan_id = (output.get("content") or {}).get("id", "")
    try:
        uuid.UUID(plan_id)
        passed = True
        evidence = f"id={plan_id}"
    except (ValueError, AttributeError):
        passed = False
        evidence = f"id={plan_id!r} is not a valid UUID"
    return CheckResult("plan_id_present", passed, float(passed), evidence)


def check_all_required_fields_present(output: dict) -> CheckResult:
    content = output.get("content") or {}
    required = ["architecture", "schedule", "tech_stack"]
    missing = [k for k in required if not content.get(k)]
    passed = len(missing) == 0
    return CheckResult("all_required_fields_present", passed, float(passed),
                       f"Missing fields: {missing or 'none'}")


def check_schema_valid(output: dict) -> CheckResult:
    from schemas.models import AgentOutput
    try:
        AgentOutput.model_validate(output)
        return CheckResult("schema_valid", True, 1.0, "AgentOutput schema valid")
    except Exception as exc:
        return CheckResult("schema_valid", False, 0.0, f"Schema error: {exc}")


ALL_CHECKS = [
    check_summary_word_count,
    check_three_paragraph_structure,
    check_no_bullet_points,
    check_no_headers,
    check_mentions_timeline,
    check_plan_id_present,
    check_all_required_fields_present,
    check_schema_valid,
]
