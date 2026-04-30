"""In-process session store: one sync Queue per active pipeline run.

The graph runs in a background thread and puts events into the queue.
The SSE route drains the queue into the HTTP response.
"""
from __future__ import annotations

import queue
from dataclasses import dataclass, field
from datetime import datetime

from rag.pipeline import RAGPipeline


@dataclass
class Session:
    session_id: str
    events: queue.Queue = field(default_factory=queue.Queue)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    hitl_paused: bool = False
    rag: "RAGPipeline | None" = None
    graph: "object | None" = None  # compiled LangGraph instance — must be reused for resume


_sessions: dict[str, Session] = {}

# Single RAG pipeline instance shared across all requests — Chroma client
# is not thread-safe for writes but reads are fine; seeding happens at startup.
_rag: RAGPipeline | None = None


def init_rag() -> None:
    global _rag
    _rag = RAGPipeline()


def get_rag() -> RAGPipeline:
    if _rag is None:
        raise RuntimeError("RAG pipeline not initialised — call init_rag() at startup")
    return _rag


def create_session(session_id: str) -> Session:
    s = Session(session_id=session_id)
    _sessions[session_id] = s
    return s


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def put_event(session_id: str, event: dict) -> None:
    s = _sessions.get(session_id)
    if s:
        s.events.put(event)


def mark_hitl_paused(session_id: str, rag: "RAGPipeline") -> None:
    s = _sessions.get(session_id)
    if s:
        s.hitl_paused = True
        s.rag = rag


def store_graph(session_id: str, graph: "object") -> None:
    s = _sessions.get(session_id)
    if s:
        s.graph = graph
