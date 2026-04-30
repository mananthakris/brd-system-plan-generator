"""Critic agent.

Reviews all agent outputs against a 5-dimension rubric and decides:
  pass   → proceed to HITL gate
  revise → loop back to plan_generator (up to max_revision_cycles)

Scoring dimensions:
  1. completeness — does the plan cover all BRD requirements?
  2. feasibility  — are choices realistic given team skills and constraints?
  3. specificity  — are recommendations concrete and actionable?
  4. consistency  — are architecture, tech stack, and plan internally consistent?
  5. scope_fit    — does the plan match BRD scope (no gold-plating, no gaps)?
"""
from __future__ import annotations

from opentelemetry import trace as otel_trace
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI

from config import settings
from schemas.models import AgentOutput, BRDInput, CriticDimension, CriticRubric


# ---------------------------------------------------------------------------
# Internal structured output schema
# ---------------------------------------------------------------------------

class _DimensionRaw(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    passed: bool


class _CriticOutput(BaseModel):
    completeness: _DimensionRaw
    feasibility: _DimensionRaw
    specificity: _DimensionRaw
    consistency: _DimensionRaw
    scope_fit: _DimensionRaw
    overall_score: float = Field(ge=0.0, le=1.0)
    revision_required: bool
    revision_notes: str | None = None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_CRITIC_SYSTEM = """\
You are a senior engineering manager reviewing a multi-agent generated engineering plan.

Score the plan across five dimensions. For each dimension: score 0.0–1.0, one specific feedback
sentence (cite a concrete example from the plan), and passed = true if score ≥ 0.60.

──────────────────────────────────────────────
1. completeness (weight 0.25)
   Does the plan address ALL functional and non-functional requirements in the BRD?
   1.0 = every stated requirement maps to at least one deliverable or architecture component
   0.0 = major requirements have no plan element

2. feasibility (weight 0.25)
   Are the technical choices realistic given team skills, timeline, and BRD constraints?
   Penalise: technologies the team has no experience with (unless flagged), unrealistic durations,
   violating explicit constraints (e.g. AWS-only, Python-only, no Kafka).
   1.0 = every choice is defensible given stated constraints

3. specificity (weight 0.20)
   Are recommendations concrete enough for an engineer to start work immediately?
   Penalise: vague components ("backend service"), generic deliverables ("implement feature"),
   missing integration points or API names.
   1.0 = every component, deliverable, and tech choice is named specifically

4. consistency (weight 0.15)
   Are the architecture, tech stack, and project plan internally consistent?
   Penalise: tech stack choices incompatible with the recommended architecture option;
   phases referencing components not in the architecture; timeline inconsistent with team size.
   1.0 = the three outputs form a coherent, non-contradictory whole

5. scope_fit (weight 0.15)
   Does the plan precisely match BRD scope — no gold-plating, no missing items?
   Penalise: implementing explicitly out-of-scope items, or missing items the BRD requires.
   1.0 = plan scope exactly matches BRD scope
──────────────────────────────────────────────

overall_score = (completeness × 0.25) + (feasibility × 0.25) + (specificity × 0.20) +
                (consistency × 0.15) + (scope_fit × 0.15)

revision_required = true if overall_score < {pass_threshold} OR any dimension score < 0.50

revision_notes: if revision_required, list the 3 most important issues as a numbered list with
specific, actionable fixes. If revision is not required, set to null.

Calibration:
  ≥ 0.85 = plan is detailed and complete; an engineer could start work from it
  0.70–0.84 = good plan; minor gaps that don't block execution
  0.55–0.69 = notable gaps; revision recommended
  < 0.55 = significant issues; revision required
"""

_CRITIC_USER = """\
--- BRD ---
Title: {title}
{brd_summary}

--- Project Plan (Plan Generator) ---
{plan_summary}

--- Architecture Design (Solution Architect) ---
{arch_summary}

--- Tech Stack Recommendation ---
{tech_stack_summary}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class CriticAgent:
    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.orchestrator_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    def run(
        self,
        brd_input: dict,
        plan_output: dict | None,
        architect_output: dict | None,
        tech_stack_output: dict | None,
    ) -> dict:
        brd = BRDInput.model_validate(brd_input)
        _span = otel_trace.get_current_span()
        _span.set_attribute("agent.name", "critic")
        _span.set_attribute("brd.id", brd.id)

        critic_raw, tokens = self._score(brd, plan_output, architect_output, tech_stack_output)

        rubric = CriticRubric(
            completeness=CriticDimension(
                name="completeness",
                score=critic_raw.completeness.score,
                feedback=critic_raw.completeness.feedback,
                passed=critic_raw.completeness.passed,
            ),
            feasibility=CriticDimension(
                name="feasibility",
                score=critic_raw.feasibility.score,
                feedback=critic_raw.feasibility.feedback,
                passed=critic_raw.feasibility.passed,
            ),
            specificity=CriticDimension(
                name="specificity",
                score=critic_raw.specificity.score,
                feedback=critic_raw.specificity.feedback,
                passed=critic_raw.specificity.passed,
            ),
            consistency=CriticDimension(
                name="consistency",
                score=critic_raw.consistency.score,
                feedback=critic_raw.consistency.feedback,
                passed=critic_raw.consistency.passed,
            ),
            scope_fit=CriticDimension(
                name="scope_fit",
                score=critic_raw.scope_fit.score,
                feedback=critic_raw.scope_fit.feedback,
                passed=critic_raw.scope_fit.passed,
            ),
            overall_score=critic_raw.overall_score,
            revision_required=critic_raw.revision_required,
            revision_notes=critic_raw.revision_notes,
        )

        output = AgentOutput(
            agent_name="critic",
            content=rubric.model_dump(),
            raw_text=(
                f"Overall: {rubric.overall_score:.2f} | "
                f"Revision required: {rubric.revision_required}"
                + (f"\nNotes: {rubric.revision_notes}" if rubric.revision_notes else "")
            ),
            model_used=settings.orchestrator_model,
            tokens_used=tokens,
        )
        return output.model_dump(mode="json")

    # ------------------------------------------------------------------

    def _score(
        self,
        brd: BRDInput,
        plan_output: dict | None,
        architect_output: dict | None,
        tech_stack_output: dict | None,
    ) -> tuple[_CriticOutput, int | None]:
        llm = self._llm.with_structured_output(_CriticOutput, include_raw=True)

        system = _CRITIC_SYSTEM.format(pass_threshold=settings.critic_pass_threshold)
        user_content = _CRITIC_USER.format(
            title=brd.title,
            brd_summary=_format_brd(brd),
            plan_summary=_format_plan(plan_output),
            arch_summary=_format_arch(architect_output),
            tech_stack_summary=_format_tech_stack(tech_stack_output),
        )

        result = llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ])
        parsed: _CriticOutput = result["parsed"]
        tokens = _extract_tokens(result["raw"])
        return parsed, tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_brd(brd: BRDInput) -> str:
    priority_types = [
        "objective",
        "functional_requirements",
        "non_functional_requirements",
        "constraints",
        "out_of_scope",
    ]
    lines: list[str] = []
    for stype in priority_types:
        matches = [s.content for s in brd.sections if s.section_type == stype]
        if matches:
            lines.append(f"[{stype.upper()}]\n{chr(10).join(matches)}")
    return "\n\n".join(lines) or brd.raw_content[:2000]


def _format_plan(plan_output: dict | None) -> str:
    if not plan_output:
        return "(plan not available)"
    content = plan_output.get("content", {})
    overview = content.get("project_overview", "")
    phases = content.get("phases", [])
    milestones = content.get("key_milestones", [])

    lines = [f"Overview: {overview}\n"]
    for p in phases:
        deliverables = "; ".join(p.get("deliverables", []))
        lines.append(
            f"Phase {p.get('phase_number')}: {p.get('name')} ({p.get('duration_weeks')}w)\n"
            f"  Deliverables: {deliverables}"
        )
    if milestones:
        lines.append(f"\nMilestones: {', '.join(milestones)}")
    return "\n".join(lines)


def _format_arch(architect_output: dict | None) -> str:
    if not architect_output:
        return "(architecture not available)"
    content = architect_output.get("content", {})
    options = content.get("options", [])
    recommended_id = content.get("recommended_option_id", "")
    rationale = content.get("recommendation_rationale", "")

    rec = next((o for o in options if o.get("option_id") == recommended_id), None)
    if not rec:
        return f"Recommended: {recommended_id}\nRationale: {rationale}"

    return (
        f"Recommended option: {rec['name']}\n"
        f"Description: {rec['description']}\n"
        f"Components: {', '.join(rec.get('high_level_components', []))}\n"
        f"Data flow: {rec.get('data_flow', '')}\n"
        f"Trade-offs: {rec.get('trade_offs', '')}\n"
        f"Rationale: {rationale}"
    )


def _format_tech_stack(tech_stack_output: dict | None) -> str:
    if not tech_stack_output:
        return "(tech stack not available)"
    content = tech_stack_output.get("content", {})
    recommended = content.get("recommended", "")
    rationale = content.get("rationale", "")
    options = content.get("options", [])

    rec = next((o for o in options if o.get("name") == recommended), None)
    if not rec:
        return f"Recommended: {recommended}\n{rationale}"

    return (
        f"Recommended: {rec['name']}\n"
        f"Rationale: {rec['rationale']}\n"
        f"Pros: {', '.join(rec.get('pros', []))}\n"
        f"Cons: {', '.join(rec.get('cons', []))}\n"
        f"Effort: {rec.get('estimated_effort', '')}\n"
        f"Overall rationale: {rationale}"
    )


def _extract_tokens(raw_message) -> int | None:
    try:
        usage = raw_message.response_metadata.get("token_usage", {})
        return usage.get("total_tokens")
    except Exception:
        return None
