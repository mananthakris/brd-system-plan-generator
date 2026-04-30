"""LangGraph hub-and-spoke orchestrator.

Graph topology:
  ingestion → plan_generator → schedule_estimator
            → solution_architect → poc_planner → tech_stack_recommender
            → critic → [revise? → back to plan_generator] → hitl → output

Phase 1: graph wiring complete; all nodes stubbed.
Phase 2: plan_generator, solution_architect, tech_stack_recommender, critic are real.
         schedule_estimator, poc_planner, hitl, output remain stubbed.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Callable

from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.semconv.trace import (
    OpenInferenceMimeTypeValues,
    OpenInferenceSpanKindValues,
    SpanAttributes,
)
from opentelemetry import trace as otel_trace

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver  # requires langgraph-checkpoint-sqlite

from config import settings
from rag.pipeline import RAGPipeline
from schemas.models import GraphState
from state.store import get_checkpointer

# ---------------------------------------------------------------------------
# Phoenix tracing — send spans to the Phoenix collector (http://localhost:6006)
# Start Phoenix separately: venv/bin/python -m phoenix.server.main serve
# Set PHOENIX_TRACING=0 to disable (e.g. in unit tests)
# ---------------------------------------------------------------------------

if os.getenv("PHOENIX_TRACING", "1") != "0":
    from phoenix.otel import register as _phoenix_register
    _phoenix_register(project_name="brd-planner")
    OpenAIInstrumentor().instrument()
    LangChainInstrumentor().instrument()

_tracer = otel_trace.get_tracer("brd-planner.agents")


@contextmanager
def _agent_span(agent_name: str, input_data: dict[str, Any]):
    """
    Wraps a block in an OpenInference AGENT span with input.value pre-set.
    Caller sets output via the returned span:
        with _agent_span("my_agent", {...}) as span:
            result = do_work()
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(result, default=str))
    Phoenix 'Add to Dataset' reads input.value and output.value to create examples.
    """
    with _tracer.start_as_current_span(agent_name) as span:
        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.AGENT.value)
        span.set_attribute(SpanAttributes.AGENT_NAME, agent_name)
        span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(input_data, default=str)[:8000])
        span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, OpenInferenceMimeTypeValues.JSON.value)
        span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, OpenInferenceMimeTypeValues.JSON.value)
        yield span


# ---------------------------------------------------------------------------
# Node stubs (Phase 1) — replace each with real agent in Phase 2
# ---------------------------------------------------------------------------

def node_ingest(state: GraphState) -> dict:
    """BRD has already been ingested before graph entry. No-op passthrough."""
    return {}


def node_plan_generator(state: GraphState, rag: RAGPipeline) -> dict:
    """Generate project phases and milestones from BRD; accepts critic revision notes on retry."""
    from agents.planning.plan_generator import PlanGeneratorAgent

    brd_input = state.get("brd_input")
    if not brd_input:
        return {"errors": ["plan_generator: brd_input missing from state"]}

    revision_notes: str | None = None
    critic = state.get("critic_output")
    if critic:
        revision_notes = (critic.get("content") or {}).get("revision_notes")

    with _agent_span("plan_generator", {"brd_input": brd_input, "revision_notes": revision_notes}) as span:
        output = PlanGeneratorAgent(rag).run(brd_input, revision_notes=revision_notes)
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(output, default=str)[:8000])

    return {
        "plan_output": output,
        "rag_context": {**state.get("rag_context", {}), "plan_generator": output.get("rag_context")},
    }


def node_schedule_estimator(state: GraphState) -> dict:
    """Consolidate plan phases + tech stack effort into a calibrated schedule."""
    from agents.planning.schedule_estimator import ScheduleEstimatorAgent

    brd_input = state.get("brd_input")
    if not brd_input:
        return {"errors": ["schedule_estimator: brd_input missing from state"]}

    with _agent_span("schedule_estimator", {
        "brd_input": brd_input,
        "plan_output": state.get("plan_output"),
        "tech_stack_output": state.get("tech_stack_output"),
    }) as span:
        output = ScheduleEstimatorAgent().run(
            brd_input=brd_input,
            plan_output=state.get("plan_output"),
            tech_stack_output=state.get("tech_stack_output"),
        )
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(output, default=str)[:8000])

    return {"schedule_output": output}


def node_solution_architect(state: GraphState, rag: RAGPipeline) -> dict:
    """Classify problem type then design high-level architecture."""
    from agents.design.solution_architect import SolutionArchitectAgent

    brd_input = state.get("brd_input")
    if not brd_input:
        return {"errors": ["solution_architect: brd_input missing from state"]}

    with _agent_span("solution_architect", {"brd_input": brd_input}) as span:
        output = SolutionArchitectAgent(rag).run(brd_input)
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(output, default=str)[:8000])

    return {
        "architect_output": output,
        "rag_context": {**state.get("rag_context", {}), "solution_architect": output.get("rag_context")},
    }


def node_poc_planner(state: GraphState) -> dict:
    """Phase 2: define PoC scope and success criteria (runs only for poc problem_type)."""
    # TODO: call agents/design/poc_planner.py
    return {
        "poc_output": {
            "agent_name": "poc_planner",
            "content": {
                "scope": "stub",
                "success_criteria": [],
                "duration_weeks": 0,
                "team_size": 0,
                "key_risks": [],
                "out_of_scope": [],
            },
            "raw_text": "stub",
            "model_used": settings.fast_model,
        }
    }


def node_tech_stack_recommender(state: GraphState, rag: RAGPipeline) -> dict:
    """Recommend 2-3 tech stack configurations grounded in current stack + team skills."""
    from agents.design.tech_stack_recommender import TechStackRecommenderAgent

    brd_input = state.get("brd_input")
    if not brd_input:
        return {"errors": ["tech_stack_recommender: brd_input missing from state"]}

    with _agent_span("tech_stack_recommender", {
        "brd_input": brd_input,
        "architect_output": state.get("architect_output"),
    }) as span:
        output = TechStackRecommenderAgent(rag).run(
            brd_input=brd_input,
            architect_output=state.get("architect_output"),
        )
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(output, default=str)[:8000])

    return {
        "tech_stack_output": output,
        "rag_context": {**state.get("rag_context", {}), "tech_stack_recommender": output.get("rag_context")},
    }


def node_critic(state: GraphState) -> dict:
    """Score all agent outputs against rubric; increment revision_count if revision required."""
    from agents.critic import CriticAgent

    brd_input = state.get("brd_input")
    if not brd_input:
        return {"errors": ["critic: brd_input missing from state"]}

    with _agent_span("critic", {
        "brd_input": brd_input,
        "plan_output": state.get("plan_output"),
        "architect_output": state.get("architect_output"),
        "tech_stack_output": state.get("tech_stack_output"),
    }) as span:
        output = CriticAgent().run(
            brd_input=brd_input,
            plan_output=state.get("plan_output"),
            architect_output=state.get("architect_output"),
            tech_stack_output=state.get("tech_stack_output"),
        )
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(output, default=str)[:8000])

    revision_required = (output.get("content") or {}).get("revision_required", False)
    current_count = state.get("revision_count", 0)

    return {
        "critic_output": output,
        "revision_count": current_count + 1 if revision_required else current_count,
    }


def node_hitl(state: GraphState) -> dict:
    """HITL gate — interrupts for Engineering Manager approval."""
    from langgraph.types import interrupt
    decision = interrupt({"message": "Awaiting Engineering Manager approval"})
    approved = decision.get("approved", False) if isinstance(decision, dict) else bool(decision)
    return {"hitl_approved": approved}


def node_output(state: GraphState) -> dict:
    """Generate executive summary and assemble the final engineering plan."""
    from agents.output.formatter import OutputFormatterAgent

    brd_input = state.get("brd_input")
    if not brd_input:
        return {"errors": ["output: brd_input missing from state"]}

    with _agent_span("output_formatter", {
        "brd_input": brd_input,
        "plan_output": state.get("plan_output"),
        "architect_output": state.get("architect_output"),
        "tech_stack_output": state.get("tech_stack_output"),
        "schedule_output": state.get("schedule_output"),
    }) as span:
        output = OutputFormatterAgent().run(
            brd_input=brd_input,
            plan_output=state.get("plan_output"),
            architect_output=state.get("architect_output"),
            tech_stack_output=state.get("tech_stack_output"),
            schedule_output=state.get("schedule_output"),
            critic_output=state.get("critic_output"),
            revision_count=state.get("revision_count", 0),
        )
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(output, default=str)[:8000])

    return {"engineering_plan": output}


# ---------------------------------------------------------------------------
# Conditional edges
# ---------------------------------------------------------------------------

def _route_after_critic(state: GraphState) -> str:
    critic = state.get("critic_output") or {}
    revision_count = state.get("revision_count", 0)
    # critic_output is an AgentOutput dict; revision_required lives in .content
    needs_revision = (critic.get("content") or {}).get("revision_required", False)

    if needs_revision and revision_count < settings.max_revision_cycles:
        return "revise"
    return "proceed"


def _route_after_hitl(state: GraphState) -> str:
    return "approved" if state.get("hitl_approved") else "rejected"


def _should_run_poc(state: GraphState) -> str:
    architect = state.get("architect_output") or {}
    problem_type = architect.get("content", {}).get("problem_type", "")
    return "poc" if problem_type == "poc" else "skip_poc"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(checkpointer: SqliteSaver | None = None, rag: RAGPipeline | None = None) -> StateGraph:
    cp = checkpointer or get_checkpointer()
    _rag = rag or RAGPipeline()

    builder = StateGraph(GraphState)

    # Nodes
    builder.add_node("ingest", node_ingest)
    builder.add_node("plan_generator", lambda state: node_plan_generator(state, _rag))
    builder.add_node("schedule_estimator", node_schedule_estimator)
    builder.add_node("solution_architect", lambda state: node_solution_architect(state, _rag))
    builder.add_node("poc_planner", node_poc_planner)
    builder.add_node("tech_stack_recommender", lambda state: node_tech_stack_recommender(state, _rag))
    builder.add_node("critic", node_critic)
    builder.add_node("hitl", node_hitl)
    builder.add_node("output", node_output)

    # Entry
    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "plan_generator")

    # Design group: plan_generator → solution_architect → optional poc_planner → tech_stack_recommender
    builder.add_edge("plan_generator", "solution_architect")
    builder.add_conditional_edges(
        "solution_architect",
        _should_run_poc,
        {"poc": "poc_planner", "skip_poc": "tech_stack_recommender"},
    )
    builder.add_edge("poc_planner", "tech_stack_recommender")

    # Schedule estimator runs after tech_stack so it has both plan + stack effort signals
    builder.add_edge("tech_stack_recommender", "schedule_estimator")
    builder.add_edge("schedule_estimator", "critic")

    # Critic → revise loop or proceed
    builder.add_conditional_edges(
        "critic",
        _route_after_critic,
        {"revise": "plan_generator", "proceed": "hitl"},
    )

    # HITL → output or end
    builder.add_conditional_edges(
        "hitl",
        _route_after_hitl,
        {"approved": "output", "rejected": END},
    )

    builder.add_edge("output", END)

    return builder.compile(checkpointer=cp)
