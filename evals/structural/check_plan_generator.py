"""Deterministic structural checks for plan_generator output."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float
    evidence: str


def check_phase_count(output: dict) -> CheckResult:
    phases = (output.get("content") or {}).get("phases", [])
    count = len(phases)
    passed = 3 <= count <= 6
    return CheckResult("phase_count_in_range", passed, float(passed),
                       f"Phase count: {count} (expected 3–6)")


def check_all_phases_have_deliverables(output: dict) -> CheckResult:
    phases = (output.get("content") or {}).get("phases", [])
    bad = [p.get("name") for p in phases if not p.get("deliverables")]
    passed = len(bad) == 0
    return CheckResult("all_phases_have_deliverables", passed, float(passed),
                       f"Phases missing deliverables: {bad or 'none'}")


def check_all_phases_have_objectives(output: dict) -> CheckResult:
    phases = (output.get("content") or {}).get("phases", [])
    bad = [p.get("name") for p in phases if len(p.get("objectives", [])) < 2]
    passed = len(bad) == 0
    return CheckResult("all_phases_have_objectives", passed, float(passed),
                       f"Phases with < 2 objectives: {bad or 'none'}")


def check_duration_bounds(output: dict) -> CheckResult:
    phases = (output.get("content") or {}).get("phases", [])
    bad = [p.get("name") for p in phases
           if not (1 <= p.get("duration_weeks", 0) <= 12)]
    passed = len(bad) == 0
    return CheckResult("duration_bounds", passed, float(passed),
                       f"Phases with out-of-range duration: {bad or 'none'}")


def check_no_circular_deps(output: dict) -> CheckResult:
    phases = (output.get("content") or {}).get("phases", [])
    name_to_idx = {p.get("name"): i for i, p in enumerate(phases)}
    adj: dict[int, list[int]] = {i: [] for i in range(len(phases))}
    for i, p in enumerate(phases):
        for dep in p.get("dependencies", []):
            if dep in name_to_idx:
                adj[i].append(name_to_idx[dep])

    visited, stack = set(), set()
    has_cycle = False

    def dfs(node: int) -> None:
        nonlocal has_cycle
        visited.add(node)
        stack.add(node)
        for nb in adj[node]:
            if nb not in visited:
                dfs(nb)
            elif nb in stack:
                has_cycle = True
        stack.discard(node)

    for node in adj:
        if node not in visited:
            dfs(node)

    passed = not has_cycle
    return CheckResult("no_circular_deps", passed, float(passed),
                       "No circular phase dependencies" if passed else "Circular dependency detected")


def check_sequential_phase_numbers(output: dict) -> CheckResult:
    phases = (output.get("content") or {}).get("phases", [])
    numbers = [p.get("phase_number") for p in phases]
    expected = list(range(1, len(phases) + 1))
    passed = sorted(numbers) == expected
    return CheckResult("sequential_phase_numbers", passed, float(passed),
                       f"Phase numbers: {numbers} (expected {expected})")


def check_key_milestones_count(output: dict) -> CheckResult:
    milestones = (output.get("content") or {}).get("key_milestones", [])
    count = len(milestones)
    passed = 3 <= count <= 5
    return CheckResult("key_milestones_count", passed, float(passed),
                       f"Milestone count: {count} (expected 3–5)")


def check_schema_valid(output: dict) -> CheckResult:
    from schemas.models import AgentOutput
    try:
        AgentOutput.model_validate(output)
        return CheckResult("schema_valid", True, 1.0, "AgentOutput schema valid")
    except Exception as exc:
        return CheckResult("schema_valid", False, 0.0, f"Schema error: {exc}")


ALL_CHECKS = [
    check_phase_count,
    check_all_phases_have_deliverables,
    check_all_phases_have_objectives,
    check_duration_bounds,
    check_no_circular_deps,
    check_sequential_phase_numbers,
    check_key_milestones_count,
    check_schema_valid,
]
