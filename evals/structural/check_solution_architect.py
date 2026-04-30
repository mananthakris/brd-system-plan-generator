"""Deterministic structural checks for solution_architect output."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float
    evidence: str


_VALID_PROBLEM_TYPES = {"greenfield", "new_feature", "migration", "integration", "poc", "enhancement"}
_VALID_COMPLEXITIES = {"low", "medium", "high"}


def check_option_count(output: dict) -> CheckResult:
    options = (output.get("content") or {}).get("options", [])
    count = len(options)
    passed = 2 <= count <= 3
    return CheckResult("option_count", passed, float(passed),
                       f"Option count: {count} (expected 2–3)")


def check_unique_option_ids(output: dict) -> CheckResult:
    options = (output.get("content") or {}).get("options", [])
    ids = [o.get("option_id") for o in options]
    passed = len(ids) == len(set(ids))
    return CheckResult("unique_option_ids", passed, float(passed),
                       f"Option IDs: {ids}")


def check_recommended_id_valid(output: dict) -> CheckResult:
    content = output.get("content") or {}
    options = content.get("options", [])
    ids = {o.get("option_id") for o in options}
    recommended = content.get("recommended_option_id")
    passed = recommended in ids
    return CheckResult("recommended_id_valid", passed, float(passed),
                       f"recommended_option_id={recommended!r}, valid ids={ids}")


def check_all_options_have_components(output: dict) -> CheckResult:
    options = (output.get("content") or {}).get("options", [])
    bad = [o.get("option_id") for o in options
           if len(o.get("high_level_components", [])) < 2]
    passed = len(bad) == 0
    return CheckResult("all_options_have_components", passed, float(passed),
                       f"Options with < 2 components: {bad or 'none'}")


def check_all_options_have_integration_points(output: dict) -> CheckResult:
    options = (output.get("content") or {}).get("options", [])
    bad = [o.get("option_id") for o in options
           if len(o.get("integration_points", [])) < 1]
    passed = len(bad) == 0
    return CheckResult("all_options_have_integration_points", passed, float(passed),
                       f"Options missing integration points: {bad or 'none'}")


def check_problem_type_valid(output: dict) -> CheckResult:
    problem_type = (output.get("content") or {}).get("problem_type", "")
    passed = problem_type in _VALID_PROBLEM_TYPES
    return CheckResult("problem_type_valid", passed, float(passed),
                       f"problem_type={problem_type!r}")


def check_classification_rationale_nonempty(output: dict) -> CheckResult:
    rationale = (output.get("content") or {}).get("classification_rationale", "")
    passed = len(rationale) > 20
    return CheckResult("classification_rationale_nonempty", passed, float(passed),
                       f"Rationale length: {len(rationale)} chars")


def check_complexity_valid(output: dict) -> CheckResult:
    options = (output.get("content") or {}).get("options", [])
    bad = [o.get("option_id") for o in options
           if o.get("estimated_complexity") not in _VALID_COMPLEXITIES]
    passed = len(bad) == 0
    return CheckResult("complexity_valid", passed, float(passed),
                       f"Options with invalid complexity: {bad or 'none'}")


def check_options_are_differentiated(output: dict) -> CheckResult:
    options = (output.get("content") or {}).get("options", [])
    names = [o.get("name", "") for o in options]
    passed = len(names) == len(set(names))
    return CheckResult("options_are_differentiated", passed, float(passed),
                       f"Option names: {names}")


def check_schema_valid(output: dict) -> CheckResult:
    from schemas.models import AgentOutput
    try:
        AgentOutput.model_validate(output)
        return CheckResult("schema_valid", True, 1.0, "AgentOutput schema valid")
    except Exception as exc:
        return CheckResult("schema_valid", False, 0.0, f"Schema error: {exc}")


ALL_CHECKS = [
    check_option_count,
    check_unique_option_ids,
    check_recommended_id_valid,
    check_all_options_have_components,
    check_all_options_have_integration_points,
    check_problem_type_valid,
    check_classification_rationale_nonempty,
    check_complexity_valid,
    check_options_are_differentiated,
    check_schema_valid,
]
