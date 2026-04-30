"""Solution Architect agent.

Three-step reasoning:
  1. Classify problem type from BRD objective + constraints.
  2. Design 2-3 competing architectural options grounded in classification + RAG context.
  3. Assemble into a decision-ready ArchitectureDesign with recommendation + rationale.

Separate LLM calls keep classification focused and inspectable as an explicit
intermediate result rather than an implicit assumption baked into the design step.
"""
from __future__ import annotations

from typing import Literal

from opentelemetry import trace as otel_trace
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import settings
from rag.pipeline import RAGPipeline
from schemas.models import (
    AgentOutput,
    ArchitectureDesign,
    ArchitectureOption,
    BRDInput,
    ProblemType,
    RAGContext,
)


# ---------------------------------------------------------------------------
# Structured output schemas (internal — not exposed to the rest of the system)
# ---------------------------------------------------------------------------

class _Classification(BaseModel):
    problem_type: Literal["greenfield", "new_feature", "migration", "integration", "poc", "enhancement"]
    rationale: str


class _ArchitectureOptionRaw(BaseModel):
    option_id: str   # "A", "B", or "C"
    name: str
    description: str
    high_level_components: list[str]
    data_flow: str
    integration_points: list[str]
    constraints_addressed: list[str]
    trade_offs: str
    estimated_complexity: Literal["low", "medium", "high"]


class _ArchitectureOutput(BaseModel):
    options: list[_ArchitectureOptionRaw]
    recommended_option_id: str
    recommendation_rationale: str


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_CLASSIFY_SYSTEM = """\
You are a Solution Architect reviewing an engineering requirements document.
Classify the type of engineering problem it describes using exactly one of the six types below.

Problem type definitions and the key question for each:

- greenfield:   Is this an entirely new standalone product, service, or platform with no prior codebase?
                Use only when there is nothing existing to build on at all.

- new_feature:  Is this a net-new capability being added to an existing product for the FIRST TIME?
                The team, platform, and infrastructure already exist, but this specific functionality
                has never been built. There is nothing to "improve" — it doesn't exist yet.
                Use this when the objective is to "build" or "create" something new within an existing system.

- migration:    Is the primary goal moving from one technology, platform, or data store to another?

- integration:  Is the primary goal connecting two or more existing systems via APIs or event streams?

- poc:          Is this explicitly scoped as a time-boxed spike or proof-of-concept to validate a hypothesis?
                The document must state or strongly imply it is NOT production-ready by design.

- enhancement:  Is this improving, optimising, or extending functionality that ALREADY EXISTS in the codebase?
                Only use this if a working version of the feature is already shipped and the goal is to make it better.

Critical distinction — new_feature vs enhancement:
  enhancement = the feature exists today; the BRD asks to improve it
  new_feature  = the feature does not exist today; the BRD asks to build it for the first time

Return your classification and a one-sentence rationale that cites specific evidence from the document.
"""

_CLASSIFY_USER = """\
Title: {title}

Objective:
{objective}

Constraints:
{constraints}

Out of scope:
{out_of_scope}
"""

_DESIGN_SYSTEM = """\
You are a Solution Architect producing a decision-ready system design for a fraud detection \
and risk decisioning platform. This BRD has been classified as a **{problem_type}** problem.

Your task is to produce 2-3 COMPETING architectural options, then recommend one.

Each option must represent a genuinely different approach — not minor variations of the same design.
Meaningful axes of difference include:
- Synchronous vs. asynchronous processing
- Managed cloud service vs. self-hosted
- Single new service vs. extension of an existing service
- Batch-oriented vs. streaming-oriented
- Monolith module vs. independent microservice

For each option provide:
- option_id: "A", "B", or "C"
- name: a short descriptive label (e.g. "Streaming-first Kafka + Tecton pipeline")
- description: 1-3 sentences summarising the approach
- high_level_components: concrete named services or modules (not generic labels like "backend")
- data_flow: a clear narrative of how data enters, transforms, and exits
- integration_points: specific external systems, internal services, or APIs touched
- constraints_addressed: for each BRD constraint, one entry explaining how this option satisfies it
- trade_offs: concise narrative of what this option gains and what it gives up
- estimated_complexity: "low" | "medium" | "high"

Then recommend one option and provide a recommendation_rationale that explains:
- Why this option best fits the BRD constraints and success criteria
- How it aligns with the company's existing stack and team skills
- What risks it avoids compared to the alternatives

Rules:
- Ground every component name in the company's known services and technology stack (see context below)
- Do not recommend the most complex option by default — favour the simplest option that satisfies requirements
- If a BRD constraint prohibits a technology, respect it in every option
- Do not introduce technologies the team has no experience with unless no alternative exists
- The recommended_option_id must match one of the option_ids you produce

Guidelines by problem type:
- greenfield:   propose full system decomposition from scratch; favour proven patterns
- new_feature:  design the new module end-to-end; identify where it plugs into the existing platform
- migration:    identify cutover strategy (strangler fig, big-bang, parallel-run) and data migration approach
- integration:  focus on data contracts, failure modes, retry/idempotency, and observability at boundaries
- poc:          keep options minimal; call out what is simplified vs. production design
- enhancement:  extend existing architecture with minimal footprint; flag cross-cutting impacts
"""

_DESIGN_USER = """\
--- Company context (from knowledge base) ---
{rag_context}

--- BRD sections ---
{brd_sections}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class SolutionArchitectAgent:
    def __init__(self, rag: RAGPipeline):
        self._rag = rag
        self._llm = ChatOpenAI(
            model=settings.orchestrator_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    def run(self, brd_input: dict) -> dict:
        """Run the classify → design pipeline.

        Accepts the serialised BRDInput dict from GraphState and returns a
        dict matching AgentOutput structure (serialised for LangGraph state).
        """
        brd = BRDInput.model_validate(brd_input)
        _span = otel_trace.get_current_span()
        _span.set_attribute("agent.name", "solution_architect")
        _span.set_attribute("brd.id", brd.id)

        # ------------------------------------------------------------------
        # Step 1 — Retrieve architecture + stack context from RAG
        # ------------------------------------------------------------------
        arch_context = self._rag.retrieve(
            query=f"architecture patterns and technology decisions for {brd.metadata.domain}",
            source_types=["architecture_decision", "current_stack"],
        )
        infra_context = self._rag.retrieve(
            query="cloud infrastructure constraints, engineering standards, and team skills",
            source_types=["cloud_infrastructure", "eng_standards"],
        )
        combined_rag = _merge_rag_contexts(arch_context, infra_context)

        # ------------------------------------------------------------------
        # Step 2 — Classify problem type
        # ------------------------------------------------------------------
        classification, classify_tokens = self._classify(brd)

        # ------------------------------------------------------------------
        # Step 3 — Design competing architectural options
        # ------------------------------------------------------------------
        arch_output, design_tokens = self._design(brd, classification, combined_rag)

        # ------------------------------------------------------------------
        # Assemble output
        # ------------------------------------------------------------------
        options = [
            ArchitectureOption(
                option_id=opt.option_id,
                name=opt.name,
                description=opt.description,
                high_level_components=opt.high_level_components,
                data_flow=opt.data_flow,
                integration_points=opt.integration_points,
                constraints_addressed=opt.constraints_addressed,
                trade_offs=opt.trade_offs,
                estimated_complexity=opt.estimated_complexity,
            )
            for opt in arch_output.options
        ]

        design = ArchitectureDesign(
            problem_type=ProblemType(classification.problem_type),
            classification_rationale=classification.rationale,
            options=options,
            recommended_option_id=arch_output.recommended_option_id,
            recommendation_rationale=arch_output.recommendation_rationale,
        )

        raw_text = (
            f"Classification: {classification.problem_type}\n"
            f"Rationale: {classification.rationale}\n\n"
            f"Options: {', '.join(o.name for o in options)}\n"
            f"Recommended: {arch_output.recommended_option_id} — {arch_output.recommendation_rationale}"
        )

        output = AgentOutput(
            agent_name="solution_architect",
            content=design.model_dump(),
            raw_text=raw_text,
            rag_context=combined_rag,
            model_used=settings.orchestrator_model,
            tokens_used=(classify_tokens or 0) + (design_tokens or 0),
        )
        return output.model_dump(mode="json")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _classify(self, brd: BRDInput) -> tuple[_Classification, int | None]:
        llm = self._llm.with_structured_output(_Classification, include_raw=True)

        user_content = _CLASSIFY_USER.format(
            title=brd.title,
            objective=_get_section(brd, "objective"),
            constraints=_get_section(brd, "constraints"),
            out_of_scope=_get_section(brd, "out_of_scope"),
        )

        result = llm.invoke([
            {"role": "system", "content": _CLASSIFY_SYSTEM},
            {"role": "user", "content": user_content},
        ])

        parsed: _Classification = result["parsed"]
        tokens = _extract_tokens(result["raw"])
        return parsed, tokens

    def _design(
        self,
        brd: BRDInput,
        classification: _Classification,
        rag_context: RAGContext,
    ) -> tuple[_ArchitectureOutput, int | None]:
        llm = self._llm.with_structured_output(_ArchitectureOutput, include_raw=True)

        system = _DESIGN_SYSTEM.format(problem_type=classification.problem_type)
        user_content = _DESIGN_USER.format(
            rag_context=_format_rag(rag_context),
            brd_sections=_format_brd_sections(brd),
        )

        result = llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ])

        parsed: _ArchitectureOutput = result["parsed"]
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
    parts = []
    for chunk, source in zip(ctx.retrieved_chunks, ctx.sources):
        parts.append(f"[source: {source}]\n{chunk}")
    return "\n\n---\n\n".join(parts)


def _merge_rag_contexts(*contexts: RAGContext) -> RAGContext:
    chunks, sources, scores = [], [], []
    for ctx in contexts:
        chunks.extend(ctx.retrieved_chunks)
        sources.extend(ctx.sources)
        scores.extend(ctx.scores)
    query = contexts[0].query if contexts else ""
    return RAGContext(
        query=query,
        retrieved_chunks=chunks,
        sources=sources,
        scores=scores,
    )


def _extract_tokens(raw_message) -> int | None:
    try:
        usage = raw_message.response_metadata.get("token_usage", {})
        return usage.get("total_tokens")
    except Exception:
        return None
