"""Tech Stack Recommender agent.

Given the BRD + the Solution Architect's recommended option, produces 2-3
concrete technology stack configurations grounded in:
  - current_stack  — what the company already uses (strongly prefer extending)
  - team_skills    — what the team knows (respect capability gaps)
  - architecture_decision — past ADRs (honour prior decisions)
"""
from __future__ import annotations

from opentelemetry import trace as otel_trace
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import settings
from rag.pipeline import RAGPipeline
from schemas.models import (
    AgentOutput,
    BRDInput,
    RAGContext,
    TechOption,
    TechStackRecommendation,
)


# ---------------------------------------------------------------------------
# Internal structured output schema
# ---------------------------------------------------------------------------

class _TechOptionRaw(BaseModel):
    name: str
    rationale: str
    pros: list[str]
    cons: list[str]
    estimated_effort: str


class _TechStackOutput(BaseModel):
    options: list[_TechOptionRaw]
    recommended: str   # must match one of the option names exactly
    rationale: str


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_STACK_SYSTEM = """\
You are a senior platform engineer producing technology stack recommendations for a software feature
at a fraud detection and risk decisioning company.

Given the BRD constraints and the Solution Architect's recommended architecture, propose 2-3 concrete
technology stack configurations. Each configuration is a complete set of technology choices for
implementing the feature — not a comparison of individual tools in isolation.

For each option provide:
- name: short descriptive label (e.g. "AWS-native managed services", "Extend existing SQS pipeline",
  "Lightweight in-process module")
- rationale: 1-2 sentences explaining the core approach
- pros: 3-5 concrete advantages in the context of this BRD and company
- cons: 2-4 concrete disadvantages or risks
- estimated_effort: realistic descriptor (e.g. "2 engineers · 4 weeks", "1 engineer · 2 weeks")

Then set recommended to exactly one of the option names, and provide a rationale explaining:
- Why this option best satisfies the BRD's functional and non-functional requirements
- How it aligns with the company's existing stack (cite specific services by name)
- What team skill constraints it respects

Rules:
- Strongly prefer extending existing technology choices over introducing new services or languages
- If the team has no experience with a technology, flag it explicitly in cons
- Never recommend options that violate BRD constraints (e.g. AWS-only, Python-only, no Kafka)
- Options must be meaningfully different approaches, not minor variations of the same design
- "estimated" means realistic — do not under-estimate to make an option look attractive
- The recommended value must exactly match one of the option names you produce
"""

_STACK_USER = """\
--- Company context (current stack, team skills, past ADRs) ---
{rag_context}

--- BRD ---
Title: {title}

{brd_sections}

--- Solution Architect's recommended option ---
{architecture_summary}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class TechStackRecommenderAgent:
    def __init__(self, rag: RAGPipeline):
        self._rag = rag
        self._llm = ChatOpenAI(
            model=settings.fast_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    def run(self, brd_input: dict, architect_output: dict | None = None) -> dict:
        brd = BRDInput.model_validate(brd_input)
        _span = otel_trace.get_current_span()
        _span.set_attribute("agent.name", "tech_stack_recommender")
        _span.set_attribute("brd.id", brd.id)

        rag_ctx = self._rag.retrieve(
            query=f"technology stack choices, team capabilities, and prior ADRs for {brd.title}",
            source_types=["current_stack", "team_skills", "architecture_decision"],
        )

        arch_summary = _extract_arch_summary(architect_output)
        stack_output, tokens = self._generate(brd, rag_ctx, arch_summary)

        options = [
            TechOption(
                name=opt.name,
                rationale=opt.rationale,
                pros=opt.pros,
                cons=opt.cons,
                estimated_effort=opt.estimated_effort,
            )
            for opt in stack_output.options
        ]

        recommendation = TechStackRecommendation(
            options=options,
            recommended=stack_output.recommended,
            rationale=stack_output.rationale,
        )

        raw_text = (
            f"Recommended: {stack_output.recommended}\n"
            f"Rationale: {stack_output.rationale}\n\n"
            + "\n".join(f"• {o.name} — {o.rationale}" for o in options)
        )

        output = AgentOutput(
            agent_name="tech_stack_recommender",
            content=recommendation.model_dump(),
            raw_text=raw_text,
            rag_context=rag_ctx,
            model_used=settings.fast_model,
            tokens_used=tokens,
        )
        return output.model_dump(mode="json")

    # ------------------------------------------------------------------

    def _generate(
        self,
        brd: BRDInput,
        rag_ctx: RAGContext,
        arch_summary: str,
    ) -> tuple[_TechStackOutput, int | None]:
        llm = self._llm.with_structured_output(_TechStackOutput, include_raw=True)
        user_content = _STACK_USER.format(
            rag_context=_format_rag(rag_ctx),
            title=brd.title,
            brd_sections=_format_brd_sections(brd),
            architecture_summary=arch_summary,
        )
        result = llm.invoke([
            {"role": "system", "content": _STACK_SYSTEM},
            {"role": "user", "content": user_content},
        ])
        parsed: _TechStackOutput = result["parsed"]
        tokens = _extract_tokens(result["raw"])
        return parsed, tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_arch_summary(architect_output: dict | None) -> str:
    if not architect_output:
        return "(architect output not available)"
    content = architect_output.get("content", {})
    options = content.get("options", [])
    recommended_id = content.get("recommended_option_id", "")
    rationale = content.get("recommendation_rationale", "")

    rec = next((o for o in options if o.get("option_id") == recommended_id), None)
    if not rec:
        return f"Recommended option: {recommended_id}\nRationale: {rationale}"

    components = "\n".join(f"  - {c}" for c in rec.get("high_level_components", []))
    return (
        f"Recommended option: {rec['name']}\n"
        f"Description: {rec['description']}\n"
        f"Key components:\n{components}\n"
        f"Data flow: {rec.get('data_flow', '')}\n"
        f"Constraints addressed: {', '.join(rec.get('constraints_addressed', []))}\n"
        f"Recommendation rationale: {rationale}"
    )


def _get_section(brd: BRDInput, section_type: str) -> str:
    matches = [s.content for s in brd.sections if s.section_type == section_type]
    return "\n\n".join(matches) if matches else "(not specified)"


def _format_brd_sections(brd: BRDInput) -> str:
    priority_types = [
        "objective",
        "functional_requirements",
        "non_functional_requirements",
        "constraints",
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
