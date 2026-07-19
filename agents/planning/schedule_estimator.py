"""Schedule Estimator agent.

Consumes plan_generator and tech_stack_recommender outputs to produce a
consolidated project schedule. Unique value beyond what the plan already has:

  - Calibrated total calendar weeks (accounts for phase overlap, not just sum)
  - Headcount derived from BRD constraints + tech stack effort signals
  - 4-6 planning assumptions the schedule depends on
  - 3-5 schedule risks with specific mitigation notes
"""
from __future__ import annotations

from opentelemetry import trace as otel_trace
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import settings
from schemas.models import AgentOutput, BRDInput, PlanPhase, ScheduleEstimate


# ---------------------------------------------------------------------------
# Internal structured output schema
# ---------------------------------------------------------------------------

class _ScheduleOutput(BaseModel):
    total_weeks: int
    total_engineers: int
    assumptions: list[str]
    risks: list[str]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SCHEDULE_SYSTEM = """\
You are a technical programme manager producing a consolidated project schedule estimate.

You have the project's phase breakdown and the technology stack recommendation.
Produce a refined schedule that goes beyond the sum of phase durations.

Provide:
- total_weeks: realistic calendar weeks from kick-off to production launch
  Phases can partially overlap (20-30%) — factor this in; total_weeks should be
  LESS than the raw sum of phase durations in most cases
- total_engineers: headcount required; cross-reference BRD constraints and tech stack effort
- assumptions: 4-6 specific planning assumptions the schedule depends on
  REQUIREMENT: every assumption MUST name at least one specific detail from the BRD or plan —
    a named service (e.g. "Aurora PostgreSQL", "ScoreIQ API"), a stakeholder role or team named in
    the BRD, a specific BRD constraint, or the stated delivery deadline.
    If the BRD does not state an exact headcount or role breakdown, derive a reasonable one from
    the stakeholder roles and tech stack effort in context, and phrase it as a derived estimate —
    do not present an invented number as if it were stated in the BRD.
  Good: "4-engineer team (2 backend, 1 data, 1 QA) inferred from the Backend/ML stakeholder roles
    and tech stack effort — no competing sprint commitments during Phases 1-2"
  Good: "Aurora PostgreSQL schema RFC submitted and DBA-approved before Phase 2 begins"
  Good: "Q3 2025 production deadline (stated in the BRD problem statement) is fixed; any slip in
    Phase 3 requires scope negotiation with the stakeholder listed as Product owner"
  Bad:  "Team will work efficiently"
  Bad:  "Infrastructure will be available on time"
- risks: 3-5 schedule risks with specific mitigation notes
  REQUIREMENT: every risk MUST (a) name the specific phase, service, or BRD constraint it relates to,
    AND (b) state a concrete mitigation action — not "monitor", "escalate", or "plan accordingly".
  Good: "Aurora schema migration in Phase 2 may require DBA review (1-2 week delay) — mitigate by submitting the schema RFC in Phase 1"
  Good: "Bureau sandbox credential provisioning could delay Phase 3 by 1-2 weeks — mitigate by requesting credentials at project kick-off alongside the Phase 1 mock"
  Bad:  "Integration may be delayed"
  Bad:  "Team may face unexpected blockers"

Rules:
- Reference actual phase names, service names, and technology names from the inputs — no generic placeholders
- Do not pad: 3 real risks are better than 5 vague ones
- total_weeks must be realistic for the stated team size — not optimistic
- Every assumption and risk must be traceable to a specific element in the BRD or plan inputs
"""

_SCHEDULE_USER = """\
--- BRD ---
Title: {title}
{brd_summary}

--- Project Phases (Plan Generator output) ---
{plan_summary}

--- Tech Stack Recommendation ---
{tech_stack_summary}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ScheduleEstimatorAgent:
    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.fast_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    def run(
        self,
        brd_input: dict,
        plan_output: dict | None,
        tech_stack_output: dict | None,
    ) -> dict:
        brd = BRDInput.model_validate(brd_input)
        _span = otel_trace.get_current_span()
        _span.set_attribute("agent.name", "schedule_estimator")
        _span.set_attribute("brd.id", brd.id)
        sched_raw, tokens = self._generate(brd, plan_output, tech_stack_output)

        # Reuse phases from plan_output — schedule estimator doesn't re-derive them
        plan_phases: list[PlanPhase] = []
        if plan_output:
            for p in (plan_output.get("content") or {}).get("phases", []):
                plan_phases.append(PlanPhase(**p))

        schedule = ScheduleEstimate(
            total_weeks=sched_raw.total_weeks,
            total_engineers=sched_raw.total_engineers,
            phases=plan_phases,
            assumptions=sched_raw.assumptions,
            risks=sched_raw.risks,
        )

        output = AgentOutput(
            agent_name="schedule_estimator",
            content=schedule.model_dump(),
            raw_text=f"{schedule.total_weeks}w · {schedule.total_engineers} engineers",
            model_used=settings.fast_model,
            tokens_used=tokens,
        )
        return output.model_dump(mode="json")

    # ------------------------------------------------------------------

    def _generate(
        self,
        brd: BRDInput,
        plan_output: dict | None,
        tech_stack_output: dict | None,
    ) -> tuple[_ScheduleOutput, int | None]:
        llm = self._llm.with_structured_output(_ScheduleOutput, include_raw=True)
        user_content = _SCHEDULE_USER.format(
            title=brd.title,
            brd_summary=_format_brd(brd),
            plan_summary=_format_plan(plan_output),
            tech_stack_summary=_format_tech_stack(tech_stack_output),
        )
        result = llm.invoke([
            {"role": "system", "content": _SCHEDULE_SYSTEM},
            {"role": "user", "content": user_content},
        ])
        parsed: _ScheduleOutput = result["parsed"]
        tokens = _extract_tokens(result["raw"])
        return parsed, tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_brd(brd: BRDInput) -> str:
    lines: list[str] = []
    for stype in (
        "objective",
        "background",
        "functional_requirements",
        "stakeholders",
        "constraints",
        "timeline",
    ):
        matches = [s.content for s in brd.sections if s.section_type == stype]
        if matches:
            lines.append(f"[{stype.upper()}]\n{chr(10).join(matches)}")
    return "\n\n".join(lines)


def _format_plan(plan_output: dict | None) -> str:
    if not plan_output:
        return "(plan not available)"
    content = plan_output.get("content", {})
    phases = content.get("phases", [])
    total = content.get("total_weeks_estimate", 0)
    lines = [f"Sum of phase durations: {total} weeks"]
    for p in phases:
        deps = ", ".join(p.get("dependencies", [])) or "none"
        lines.append(f"  Phase {p['phase_number']}: {p['name']} — {p['duration_weeks']}w (deps: {deps})")
    return "\n".join(lines)


def _format_tech_stack(tech_stack_output: dict | None) -> str:
    if not tech_stack_output:
        return "(tech stack not available)"
    content = tech_stack_output.get("content", {})
    recommended = content.get("recommended", "")
    options = content.get("options", [])
    rec = next((o for o in options if o.get("name") == recommended), None)
    if not rec:
        return f"Recommended: {recommended}"
    return f"Recommended: {rec['name']} — Effort: {rec.get('estimated_effort', 'unknown')}"


def _extract_tokens(raw_message) -> int | None:
    try:
        usage = raw_message.response_metadata.get("token_usage", {})
        return usage.get("total_tokens")
    except Exception:
        return None
