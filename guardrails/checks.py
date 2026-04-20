"""Cross-cutting guardrail checks applied at ingestion and agent output boundaries."""
from __future__ import annotations

import re
from typing import Any

from schemas.models import AgentOutput, BRDInput


class GuardrailError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

_MIN_CONTENT_LENGTH = 200
_MAX_CONTENT_LENGTH = 150_000  # ~100k tokens safety ceiling

_FORBIDDEN_PATTERNS = [
    r"(?i)ignore\s+(previous|all)\s+instructions",
    r"(?i)disregard\s+(your|the)\s+(system\s+)?prompt",
    r"(?i)you\s+are\s+now\s+a\s+different",
    r"(?i)jailbreak",
]


def validate_brd_input(brd: BRDInput) -> None:
    """Raise GuardrailError if the BRD input fails basic checks."""
    _check_content_length(brd.raw_content)
    _check_prompt_injection(brd.raw_content)
    _check_prompt_injection(brd.title)

    if not brd.sections:
        raise GuardrailError("BRD has no classified sections — classification may have failed.")

    if not brd.metadata.domain or brd.metadata.domain == "unknown":
        raise GuardrailError("BRD metadata domain is unset — tagger may have failed.")


def _check_content_length(text: str) -> None:
    if len(text) < _MIN_CONTENT_LENGTH:
        raise GuardrailError(
            f"Document too short ({len(text)} chars). Minimum: {_MIN_CONTENT_LENGTH}."
        )
    if len(text) > _MAX_CONTENT_LENGTH:
        raise GuardrailError(
            f"Document too long ({len(text)} chars). Maximum: {_MAX_CONTENT_LENGTH}."
        )


def _check_prompt_injection(text: str) -> None:
    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, text):
            raise GuardrailError(
                f"Input contains a potential prompt injection pattern: {pattern!r}"
            )


# ---------------------------------------------------------------------------
# Agent output validation
# ---------------------------------------------------------------------------

_REQUIRED_KEYS_BY_AGENT: dict[str, list[str]] = {
    "plan_generator": ["phases", "summary"],
    "schedule_estimator": ["total_weeks", "phases"],
    "solution_architect": ["problem_type", "high_level_components", "data_flow"],
    "poc_planner": ["scope", "success_criteria", "duration_weeks"],
    "tech_stack_recommender": ["options", "recommended"],
    "critic": ["overall_score", "revision_required"],
}


def validate_agent_output(output: AgentOutput) -> None:
    """Raise GuardrailError if an agent output is missing required keys."""
    required = _REQUIRED_KEYS_BY_AGENT.get(output.agent_name, [])
    missing = [k for k in required if k not in output.content]
    if missing:
        raise GuardrailError(
            f"Agent '{output.agent_name}' output missing required keys: {missing}"
        )
    _check_no_hallucination_markers(output.raw_text)


def _check_no_hallucination_markers(text: str) -> None:
    """Flag obvious LLM uncertainty phrases that shouldn't appear in structured outputs."""
    markers = [
        r"(?i)i (don't|do not|cannot|can't) (know|determine|say)",
        r"(?i)i'm not sure",
        r"(?i)as an ai",
        r"(?i)i (was|am) trained",
    ]
    for pattern in markers:
        if re.search(pattern, text):
            raise GuardrailError(
                f"Agent output contains a hallucination/refusal marker: {pattern!r}"
            )


# ---------------------------------------------------------------------------
# Schema compliance
# ---------------------------------------------------------------------------

def check_schema_compliance(data: Any, model_class: type) -> None:
    """Validate that a dict can be parsed into a Pydantic model."""
    try:
        model_class.model_validate(data)
    except Exception as exc:
        raise GuardrailError(f"Schema compliance failure for {model_class.__name__}: {exc}") from exc
