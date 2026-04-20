"""LangGraph hub-and-spoke orchestrator.

Graph topology:
  ingestion → plan_generator → schedule_estimator
            → solution_architect → poc_planner → tech_stack_recommender
            → critic → [revise? → back to plan_generator] → hitl → output

Phase 1: graph wiring complete; all nodes stubbed.
Phase 2: solution_architect node is real; remaining nodes still stubbed.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from config import settings
from rag.pipeline import RAGPipeline
from schemas.models import GraphState
from state.store import get_checkpointer


# ---------------------------------------------------------------------------
# Node stubs (Phase 1) — replace each with real agent in Phase 2
# ---------------------------------------------------------------------------

def node_ingest(state: GraphState) -> dict:
    """BRD has already been ingested before graph entry. No-op passthrough."""
    return {}


def node_plan_generator(state: GraphState) -> dict:
    """Phase 2: generate project phases and milestones from BRD."""
    # TODO: call agents/planning/plan_generator.py
    brd_title = (state.get("brd_input") or {}).get("title", "unknown")
    return {
        "plan_output": {
            "agent_name": "plan_generator",
            "content": {"phases": [], "summary": f"STUB plan for: {brd_title}"},
            "raw_text": "stub",
            "model_used": settings.agent_model,
        }
    }


def node_schedule_estimator(state: GraphState) -> dict:
    """Phase 2: estimate effort and timeline from plan phases."""
    # TODO: call agents/planning/schedule_estimator.py
    return {
        "schedule_output": {
            "agent_name": "schedule_estimator",
            "content": {"total_weeks": 0, "phases": [], "assumptions": [], "risks": []},
            "raw_text": "stub",
            "model_used": settings.fast_model,
        }
    }


def node_solution_architect(state: GraphState, rag: RAGPipeline) -> dict:
    """Classify problem type then design high-level architecture."""
    from agents.design.solution_architect import SolutionArchitectAgent

    brd_input = state.get("brd_input")
    if not brd_input:
        return {"errors": ["solution_architect: brd_input missing from state"]}

    output = SolutionArchitectAgent(rag).run(brd_input)
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


def node_tech_stack_recommender(state: GraphState) -> dict:
    """Phase 2: recommend 2–3 tech stack options with trade-offs."""
    # TODO: call agents/design/tech_stack_recommender.py
    return {
        "tech_stack_output": {
            "agent_name": "tech_stack_recommender",
            "content": {"options": [], "recommended": "stub", "rationale": "stub"},
            "raw_text": "stub",
            "model_used": settings.fast_model,
        }
    }


def node_critic(state: GraphState) -> dict:
    """Phase 2: score all outputs against rubric; decide pass/revise."""
    # TODO: call agents/critic.py
    return {
        "critic_output": {
            "overall_score": 0.85,
            "revision_required": False,
            "revision_notes": None,
            "completeness": {"name": "completeness", "score": 0.85, "feedback": "stub", "passed": True},
            "feasibility": {"name": "feasibility", "score": 0.85, "feedback": "stub", "passed": True},
            "specificity": {"name": "specificity", "score": 0.85, "feedback": "stub", "passed": True},
            "consistency": {"name": "consistency", "score": 0.85, "feedback": "stub", "passed": True},
            "scope_fit": {"name": "scope_fit", "score": 0.85, "feedback": "stub", "passed": True},
        },
        "revision_count": state.get("revision_count", 0),
    }


def node_hitl(state: GraphState) -> dict:
    """Human-in-the-loop gate. LangGraph interrupt() will pause here in Phase 4."""
    # TODO: implement interrupt() and resume logic
    print("\n[HITL] Engineering plan is ready for review.")
    print("       In Phase 4 this will use LangGraph interrupt() to pause for EM approval.")
    return {"hitl_approved": True}


def node_output(state: GraphState) -> dict:
    """Assemble the final EngineeringPlan."""
    # TODO: call output/formatter.py in Phase 4
    import uuid
    from datetime import datetime

    brd = state.get("brd_input") or {}
    return {
        "engineering_plan": {
            "id": str(uuid.uuid4()),
            "brd_id": brd.get("id", "unknown"),
            "title": f"Engineering Plan: {brd.get('title', 'unknown')}",
            "problem_type": (state.get("architect_output") or {}).get("content", {}).get("problem_type", "enhancement"),
            "executive_summary": "STUB — Phase 4 will assemble from agent outputs.",
            "architecture": (state.get("architect_output") or {}).get("content", {}),
            "schedule": (state.get("schedule_output") or {}).get("content", {}),
            "tech_stack": (state.get("tech_stack_output") or {}).get("content", {}),
            "revision_count": state.get("revision_count", 0),
            "critic_score": (state.get("critic_output") or {}).get("overall_score"),
            "created_at": datetime.utcnow().isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# Conditional edges
# ---------------------------------------------------------------------------

def _route_after_critic(state: GraphState) -> str:
    critic = state.get("critic_output") or {}
    revision_count = state.get("revision_count", 0)
    needs_revision = critic.get("revision_required", False)

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
    builder.add_node("plan_generator", node_plan_generator)
    builder.add_node("schedule_estimator", node_schedule_estimator)
    builder.add_node("solution_architect", lambda state: node_solution_architect(state, _rag))
    builder.add_node("poc_planner", node_poc_planner)
    builder.add_node("tech_stack_recommender", node_tech_stack_recommender)
    builder.add_node("critic", node_critic)
    builder.add_node("hitl", node_hitl)
    builder.add_node("output", node_output)

    # Entry
    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "plan_generator")

    # Planning group (sequential)
    builder.add_edge("plan_generator", "schedule_estimator")
    builder.add_edge("schedule_estimator", "solution_architect")

    # Design group: solution_architect → optional poc_planner → tech_stack_recommender
    builder.add_conditional_edges(
        "solution_architect",
        _should_run_poc,
        {"poc": "poc_planner", "skip_poc": "tech_stack_recommender"},
    )
    builder.add_edge("poc_planner", "tech_stack_recommender")
    builder.add_edge("tech_stack_recommender", "critic")

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
