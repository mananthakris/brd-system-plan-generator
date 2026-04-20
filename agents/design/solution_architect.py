"""Solution Architect agent.

Two-step reasoning:
  1. Classify problem type from BRD objective + constraints.
  2. Design high-level architecture grounded in classification + RAG context.

Separate LLM calls keep each step focused and make the classification
an explicit, inspectable intermediate result rather than an implicit assumption.
"""
from __future__ import annotations

from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import settings
from rag.pipeline import RAGPipeline
from schemas.models import AgentOutput, ArchitectureDesign, BRDInput, ProblemType, RAGContext


# ---------------------------------------------------------------------------
# Structured output schemas (internal — not exposed to the rest of the system)
# ---------------------------------------------------------------------------

class _Classification(BaseModel):
    problem_type: Literal["greenfield", "migration", "integration", "poc", "enhancement"]
    rationale: str


class _ArchitectureOutput(BaseModel):
    high_level_components: list[str]
    data_flow: str
    integration_points: list[str]
    constraints_addressed: list[str]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_CLASSIFY_SYSTEM = """\
You are a Solution Architect reviewing an engineering requirements document.
Classify the type of engineering problem it describes.

Problem type definitions:
- greenfield:   an entirely new product or system built from scratch
- migration:    moving data, services, or a codebase from one technology or platform to another
- integration:  connecting existing internal or external systems via APIs, events, or data pipelines
- poc:          a time-boxed proof-of-concept or spike to validate a hypothesis before full build
- enhancement:  adding features to or improving a well-defined area of an existing system

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
You are a Solution Architect producing a high-level architecture design.
This has been classified as a **{problem_type}** problem.

Guidelines by problem type:
- greenfield:   propose full system decomposition; favour proven patterns over novelty
- migration:    identify cutover strategy (strangler fig, big-bang, parallel-run) and data migration approach
- integration:  focus on data contracts, failure modes, retry/idempotency, and observability at boundaries
- poc:          keep architecture minimal; call out what is deliberately simplified vs. production design
- enhancement:  extend existing architecture; flag any cross-cutting impacts on other services

Rules:
- Ground every recommendation in the company context provided below.
- Do not introduce technologies the team has no experience with unless no alternative exists.
- If a BRD constraint prohibits a technology or approach, explicitly address it.
- high_level_components: concrete named services/modules/layers (not generic labels like "backend")
- data_flow: a clear narrative of how data enters, transforms, and exits the system
- integration_points: name the specific external systems, internal services, or APIs touched
- constraints_addressed: for each BRD constraint, one entry explaining how the design satisfies it
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
        """Run the two-step classify → design pipeline.

        Accepts the serialised BRDInput dict from GraphState and returns a
        dict matching AgentOutput structure (serialised for LangGraph state).
        """
        brd = BRDInput.model_validate(brd_input)

        # ------------------------------------------------------------------
        # Step 1 — Retrieve architecture + stack context from RAG
        # ------------------------------------------------------------------
        arch_context = self._rag.retrieve(
            query=f"architecture patterns and technology decisions for {brd.metadata.domain}",
            source_types=["architecture_decision", "current_stack"],
        )
        infra_context = self._rag.retrieve(
            query="cloud infrastructure constraints and engineering standards",
            source_types=["cloud_infrastructure", "eng_standards"],
        )
        combined_rag = _merge_rag_contexts(arch_context, infra_context)

        # ------------------------------------------------------------------
        # Step 2 — Classify problem type
        # ------------------------------------------------------------------
        classification, classify_tokens = self._classify(brd)

        # ------------------------------------------------------------------
        # Step 3 — Design architecture
        # ------------------------------------------------------------------
        architecture, design_tokens = self._design(brd, classification, combined_rag)

        # ------------------------------------------------------------------
        # Assemble output
        # ------------------------------------------------------------------
        design = ArchitectureDesign(
            problem_type=ProblemType(classification.problem_type),
            high_level_components=architecture.high_level_components,
            data_flow=architecture.data_flow,
            integration_points=architecture.integration_points,
            constraints_addressed=architecture.constraints_addressed,
        )

        raw_text = (
            f"Classification: {classification.problem_type}\n"
            f"Rationale: {classification.rationale}\n\n"
            f"Data flow: {architecture.data_flow}"
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
    # Use the first context's query as representative
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
