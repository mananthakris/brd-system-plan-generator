"""Plan Generator agent.

Reads the BRD and produces a structured multi-phase project plan:
  - 3-6 phases with objectives, deliverables, and duration estimates
  - Sequential dependency graph between phases
  - Project overview summary and key milestones

When revision_notes are supplied (from the Critic on a second pass), they are
injected into the prompt so the agent addresses the specific gaps identified.
"""
from __future__ import annotations

from opentelemetry import trace as otel_trace
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import settings
from prompts.registry import get_prompt
from rag.pipeline import RAGPipeline
from schemas.models import AgentOutput, BRDInput, PlanPhase, RAGContext


# ---------------------------------------------------------------------------
# Internal structured output schema
# ---------------------------------------------------------------------------

class _PhaseRaw(BaseModel):
    phase_number: int
    name: str
    objectives: list[str]
    deliverables: list[str]
    duration_weeks: int
    dependencies: list[str]


class _PlanOutput(BaseModel):
    project_overview: str
    phases: list[_PhaseRaw]
    key_milestones: list[str]


# ---------------------------------------------------------------------------
# Prompts (see prompts/registry.py — bump version there when editing)
# ---------------------------------------------------------------------------

_PLAN_USER = """\
--- Company context (team skills, past BRD patterns) ---
{rag_context}

--- BRD ---
Title: {title}

{brd_sections}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class PlanGeneratorAgent:
    def __init__(self, rag: RAGPipeline):
        self._rag = rag
        self._llm = ChatOpenAI(
            model=settings.agent_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    def run(self, brd_input: dict, revision_notes: str | None = None) -> dict:
        brd = BRDInput.model_validate(brd_input)
        _span = otel_trace.get_current_span()
        _span.set_attribute("agent.name", "plan_generator")
        _span.set_attribute("brd.id", brd.id)

        rag_ctx = self._rag.retrieve(
            query=f"project planning phases milestones deliverables for {brd.title}",
            source_types=["past_brd", "team_skills", "domain_context"],
        )

        plan_output, tokens = self._generate(brd, rag_ctx, revision_notes)

        phases = [
            PlanPhase(
                phase_number=p.phase_number,
                name=p.name,
                objectives=p.objectives,
                deliverables=p.deliverables,
                duration_weeks=p.duration_weeks,
                dependencies=p.dependencies,
            )
            for p in plan_output.phases
        ]

        content = {
            "project_overview": plan_output.project_overview,
            "phases": [ph.model_dump() for ph in phases],
            "key_milestones": plan_output.key_milestones,
            "total_phases": len(phases),
            "total_weeks_estimate": sum(p.duration_weeks for p in phases),
        }

        raw_text = (
            f"Overview: {plan_output.project_overview}\n\n"
            + "\n".join(
                f"Phase {p.phase_number}: {p.name} ({p.duration_weeks}w)"
                for p in phases
            )
        )

        output = AgentOutput(
            agent_name="plan_generator",
            content=content,
            raw_text=raw_text,
            rag_context=rag_ctx,
            model_used=settings.agent_model,
            tokens_used=tokens,
        )
        return output.model_dump(mode="json")

    # ------------------------------------------------------------------

    def _generate(
        self,
        brd: BRDInput,
        rag_ctx: RAGContext,
        revision_notes: str | None,
    ) -> tuple[_PlanOutput, int | None]:
        llm = self._llm.with_structured_output(_PlanOutput, include_raw=True)

        if revision_notes:
            system = get_prompt("plan_generator", "system_revision").format(revision_notes=revision_notes)
        else:
            system = get_prompt("plan_generator")

        user_content = _PLAN_USER.format(
            rag_context=_format_rag(rag_ctx),
            title=brd.title,
            brd_sections=_format_brd_sections(brd),
        )

        result = llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ])
        parsed: _PlanOutput = result["parsed"]
        tokens = _extract_tokens(result["raw"])
        return parsed, tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_section(brd: BRDInput, section_type: str) -> str:
    matches = [s.content for s in brd.sections if s.section_type == section_type]
    return "\n\n".join(matches) if matches else "(not specified)"


def _format_brd_sections(brd: BRDInput) -> str:
    priority_types = [
        "objective",
        "background",
        "functional_requirements",
        "non_functional_requirements",
        "constraints",
        "timeline",
        "risks",
        "out_of_scope",
    ]
    lines: list[str] = []
    for stype in priority_types:
        content = _get_section(brd, stype)
        if content != "(not specified)":
            lines.append(f"[{stype.upper()}]\n{content}")
    return "\n\n".join(lines)


def _format_rag(ctx: RAGContext) -> str:
    if not ctx.retrieved_chunks:
        return "(no relevant context retrieved)"
    parts = [f"[source: {src}]\n{chunk}" for chunk, src in zip(ctx.retrieved_chunks, ctx.sources)]
    return "\n\n---\n\n".join(parts)


def _extract_tokens(raw_message) -> int | None:
    try:
        usage = raw_message.response_metadata.get("token_usage", {})
        return usage.get("total_tokens")
    except Exception:
        return None
