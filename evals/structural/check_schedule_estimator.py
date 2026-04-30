"""Deterministic structural checks for schedule_estimator output."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float
    evidence: str


def check_total_weeks_positive(output: dict) -> CheckResult:
    weeks = (output.get("content") or {}).get("total_weeks", 0)
    passed = isinstance(weeks, int) and weeks >= 1
    return CheckResult("total_weeks_positive", passed, float(passed),
                       f"total_weeks={weeks}")


def check_engineers_positive(output: dict) -> CheckResult:
    engineers = (output.get("content") or {}).get("total_engineers", 0)
    passed = isinstance(engineers, int) and engineers >= 1
    return CheckResult("engineers_positive", passed, float(passed),
                       f"total_engineers={engineers}")


def check_weeks_less_than_phase_sum(output: dict) -> CheckResult:
    content = output.get("content") or {}
    total = content.get("total_weeks", 0)
    phases = content.get("phases", [])
    phase_sum = sum(p.get("duration_weeks", 0) for p in phases)
    if phase_sum == 0:
        return CheckResult("weeks_less_than_phase_sum", True, 1.0,
                           "No phases to compare against")
    passed = total < phase_sum
    return CheckResult("weeks_less_than_phase_sum", passed, float(passed),
                       f"total_weeks={total} vs phase_sum={phase_sum} (overlap expected)")


def check_assumptions_count(output: dict) -> CheckResult:
    assumptions = (output.get("content") or {}).get("assumptions", [])
    count = len(assumptions)
    passed = 4 <= count <= 6
    return CheckResult("assumptions_count", passed, float(passed),
                       f"Assumption count: {count} (expected 4–6)")


def check_risks_count(output: dict) -> CheckResult:
    risks = (output.get("content") or {}).get("risks", [])
    count = len(risks)
    passed = 3 <= count <= 5
    return CheckResult("risks_count", passed, float(passed),
                       f"Risk count: {count} (expected 3–5)")


_VAGUE_PATTERNS = [
    r"(?i)team will work",
    r"(?i)things go smoothly",
    r"(?i)no major issues",
    r"(?i)everything goes (as )?planned",
]


def check_no_vague_assumptions(output: dict) -> CheckResult:
    assumptions = (output.get("content") or {}).get("assumptions", [])
    bad = [a for a in assumptions
           if any(re.search(p, a) for p in _VAGUE_PATTERNS)]
    passed = len(bad) == 0
    return CheckResult("no_vague_assumptions", passed, float(passed),
                       f"Vague assumptions: {bad or 'none'}")


def check_schema_valid(output: dict) -> CheckResult:
    from schemas.models import AgentOutput
    try:
        AgentOutput.model_validate(output)
        return CheckResult("schema_valid", True, 1.0, "AgentOutput schema valid")
    except Exception as exc:
        return CheckResult("schema_valid", False, 0.0, f"Schema error: {exc}")


ALL_CHECKS = [
    check_total_weeks_positive,
    check_engineers_positive,
    check_weeks_less_than_phase_sum,
    check_assumptions_count,
    check_risks_count,
    check_no_vague_assumptions,
    check_schema_valid,
]
