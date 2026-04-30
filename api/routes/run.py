"""POST /api/run — ingest a BRD and start the pipeline in a background thread.
POST /api/hitl/{session_id} — submit approve/reject decision at HITL gate.
"""
from __future__ import annotations

import os
import tempfile
import threading
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from api.session import create_session, get_rag, get_session, mark_hitl_paused, put_event, store_graph

router = APIRouter()

# Nodes whose outputs are stubs — used to tag SSE events so the UI can grey them out.
_STUB_NODES = {
    "poc_planner",
}


# ---------------------------------------------------------------------------
# Run endpoint
# ---------------------------------------------------------------------------

@router.post("/run")
async def run_pipeline(
    title: str = Form(...),
    brd_text: Optional[str] = Form(None),
    brd_file: Optional[UploadFile] = File(None),
):
    if not brd_text and not brd_file:
        raise HTTPException(status_code=400, detail="Provide either brd_text or brd_file")

    session_id = str(uuid.uuid4())
    create_session(session_id)

    tmp_path: str | None = None
    if brd_file:
        suffix = os.path.splitext(brd_file.filename or "")[1] or ".txt"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(await brd_file.read())
        tmp.close()
        tmp_path = tmp.name

    rag = get_rag()

    thread = threading.Thread(
        target=_run_pipeline_sync,
        args=(session_id, title, brd_text, tmp_path, rag),
        daemon=True,
    )
    thread.start()

    return {"session_id": session_id}


# ---------------------------------------------------------------------------
# HITL decision endpoint
# ---------------------------------------------------------------------------

class HitlDecision(BaseModel):
    approved: bool


@router.post("/hitl/{session_id}")
async def submit_hitl_decision(session_id: str, body: HitlDecision):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.hitl_paused:
        raise HTTPException(status_code=400, detail="Pipeline is not paused at HITL gate")

    session.hitl_paused = False

    thread = threading.Thread(
        target=_resume_pipeline_sync,
        args=(session_id, body.approved),
        daemon=True,
    )
    thread.start()

    return {"ok": True}


# ---------------------------------------------------------------------------
# Pipeline runner (initial)
# ---------------------------------------------------------------------------

def _run_pipeline_sync(
    session_id: str,
    title: str,
    brd_text: str | None,
    tmp_path: str | None,
    rag,
) -> None:
    from ingestion.pipeline import ingest
    from agents.orchestrator import build_graph

    def emit(event: dict) -> None:
        put_event(session_id, {**event, "timestamp": datetime.utcnow().isoformat()})

    try:
        brd_input = ingest(
            source=tmp_path,
            raw_text=brd_text if not tmp_path else None,
            title=title,
        )
        if tmp_path:
            os.unlink(tmp_path)

        emit({
            "type": "pipeline_start",
            "session_id": session_id,
            "brd_title": brd_input.title,
            "brd_id": brd_input.id,
            "problem_type_hint": brd_input.metadata.problem_type,
            "complexity": brd_input.metadata.complexity,
            "section_count": len(brd_input.sections),
        })

        initial_state: dict = {
            "brd_input": brd_input.model_dump(mode="json"),
            "rag_context": {},
            "plan_output": None,
            "schedule_output": None,
            "architect_output": None,
            "poc_output": None,
            "tech_stack_output": None,
            "critic_output": None,
            "engineering_plan": None,
            "revision_count": 0,
            "hitl_approved": False,
            "errors": [],
        }

        graph = build_graph(rag=rag)
        store_graph(session_id, graph)  # must reuse this exact instance on resume (MemorySaver is in-process)
        config = {"configurable": {"thread_id": session_id}}
        revision_count = 0
        hit_interrupt = False

        for step in graph.stream(initial_state, config=config):
            node_name = list(step.keys())[0]

            if node_name == "__interrupt__":
                hit_interrupt = True
                mark_hitl_paused(session_id, rag)
                emit({"type": "hitl_pending"})
                break

            if node_name.startswith("__"):
                continue

            state_delta = step[node_name]
            if isinstance(state_delta, dict) and "revision_count" in state_delta:
                revision_count = state_delta["revision_count"]

            emit({
                "type": "node_complete",
                "node": node_name,
                "is_stub": node_name in _STUB_NODES,
                "output": state_delta,
                "revision_count": revision_count,
            })

        if not hit_interrupt:
            emit({"type": "pipeline_complete"})

    except Exception as exc:
        import traceback
        traceback.print_exc()
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        emit({"type": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Pipeline resume (after HITL decision)
# ---------------------------------------------------------------------------

def _resume_pipeline_sync(session_id: str, approved: bool) -> None:
    from langgraph.types import Command

    def emit(event: dict) -> None:
        put_event(session_id, {**event, "timestamp": datetime.utcnow().isoformat()})

    try:
        session = get_session(session_id)
        graph = session.graph if session else None
        if graph is None:
            emit({"type": "error", "message": "session graph not found — cannot resume"})
            return
        config = {"configurable": {"thread_id": session_id}}
        revision_count = 0

        if not approved:
            emit({"type": "pipeline_rejected"})
            return

        for step in graph.stream(Command(resume={"approved": True}), config=config):
            node_name = list(step.keys())[0]

            if node_name.startswith("__"):
                continue

            state_delta = step[node_name]
            if isinstance(state_delta, dict) and "revision_count" in state_delta:
                revision_count = state_delta["revision_count"]

            emit({
                "type": "node_complete",
                "node": node_name,
                "is_stub": node_name in _STUB_NODES,
                "output": state_delta,
                "revision_count": revision_count,
            })

        emit({"type": "pipeline_complete"})

    except Exception as exc:
        import traceback
        traceback.print_exc()
        emit({"type": "error", "message": str(exc)})
