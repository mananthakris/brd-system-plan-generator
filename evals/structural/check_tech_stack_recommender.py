"""Deterministic structural checks for tech_stack_recommender output."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float
    evidence: str


_EFFORT_KEYWORDS = re.compile(r"\b(week|engineer|sprint|month)\b", re.IGNORECASE)


def check_option_count(output: dict) -> CheckResult:
    options = (output.get("content") or {}).get("options", [])
    count = len(options)
    passed = 2 <= count <= 3
    return CheckResult("option_count", passed, float(passed),
                       f"Option count: {count} (expected 2–3)")


def check_recommended_matches_option(output: dict) -> CheckResult:
    content = output.get("content") or {}
    options = content.get("options", [])
    names = {o.get("name") for o in options}
    recommended = content.get("recommended")
    passed = recommended in names
    return CheckResult("recommended_matches_option", passed, float(passed),
                       f"recommended={recommended!r}, option names={names}")


def check_all_options_have_pros_cons(output: dict) -> CheckResult:
    options = (output.get("content") or {}).get("options", [])
    bad = [o.get("name") for o in options
           if len(o.get("pros", [])) < 2 or len(o.get("cons", [])) < 1]
    passed = len(bad) == 0
    return CheckResult("all_options_have_pros_cons", passed, float(passed),
                       f"Options with insufficient pros/cons: {bad or 'none'}")


def check_effort_mentions_numbers(output: dict) -> CheckResult:
    options = (output.get("content") or {}).get("options", [])
    bad = [o.get("name") for o in options
           if not _EFFORT_KEYWORDS.search(o.get("estimated_effort", ""))]
    passed = len(bad) == 0
    return CheckResult("effort_mentions_numbers", passed, float(passed),
                       f"Options with vague effort estimates: {bad or 'none'}")


def check_schema_valid(output: dict) -> CheckResult:
    from schemas.models import AgentOutput
    try:
        AgentOutput.model_validate(output)
        return CheckResult("schema_valid", True, 1.0, "AgentOutput schema valid")
    except Exception as exc:
        return CheckResult("schema_valid", False, 0.0, f"Schema error: {exc}")


ALL_CHECKS = [
    check_option_count,
    check_recommended_matches_option,
    check_all_options_have_pros_cons,
    check_effort_mentions_numbers,
    check_schema_valid,
]
