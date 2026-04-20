"""LangGraph checkpointer and session/revision metadata store."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from config import settings


def get_checkpointer() -> SqliteSaver:
    """Return a SqliteSaver for LangGraph state persistence."""
    db_path = Path(settings.sqlite_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(db_path))


class StateStore:
    """Lightweight SQLite store for session metadata and revision history.

    Separate from LangGraph checkpoints — stores human-readable records
    for audit, HITL review, and future eval harness use.
    """

    def __init__(self, db_path: str | None = None):
        path = db_path or settings.sqlite_db_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                brd_id       TEXT NOT NULL,
                brd_title    TEXT,
                status       TEXT DEFAULT 'in_progress',
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS revisions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                revision_num   INTEGER NOT NULL,
                critic_score   REAL,
                revision_notes TEXT,
                agent_outputs  TEXT,
                created_at     TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS hitl_reviews (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT NOT NULL,
                reviewer     TEXT,
                decision     TEXT NOT NULL,
                comments     TEXT,
                reviewed_at  TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, session_id: str, brd_id: str, brd_title: str = "") -> None:
        now = _now()
        self._conn.execute(
            "INSERT OR IGNORE INTO sessions VALUES (?, ?, ?, 'in_progress', ?, ?)",
            (session_id, brd_id, brd_title, now, now),
        )
        self._conn.commit()

    def update_session_status(self, session_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET status=?, updated_at=? WHERE session_id=?",
            (status, _now(), session_id),
        )
        self._conn.commit()

    def get_session(self, session_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        if not row:
            return None
        cols = ["session_id", "brd_id", "brd_title", "status", "created_at", "updated_at"]
        return dict(zip(cols, row))

    # ------------------------------------------------------------------
    # Revisions
    # ------------------------------------------------------------------

    def record_revision(
        self,
        session_id: str,
        revision_num: int,
        critic_score: float | None,
        revision_notes: str | None,
        agent_outputs: dict | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO revisions (session_id, revision_num, critic_score, revision_notes, agent_outputs, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id,
                revision_num,
                critic_score,
                revision_notes,
                json.dumps(agent_outputs or {}),
                _now(),
            ),
        )
        self._conn.commit()

    def get_revisions(self, session_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM revisions WHERE session_id=? ORDER BY revision_num", (session_id,)
        ).fetchall()
        cols = ["id", "session_id", "revision_num", "critic_score", "revision_notes", "agent_outputs", "created_at"]
        return [dict(zip(cols, row)) for row in rows]

    # ------------------------------------------------------------------
    # HITL
    # ------------------------------------------------------------------

    def record_hitl_review(
        self,
        session_id: str,
        decision: str,
        reviewer: str = "",
        comments: str = "",
    ) -> None:
        self._conn.execute(
            "INSERT INTO hitl_reviews (session_id, reviewer, decision, comments, reviewed_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, reviewer, decision, comments, _now()),
        )
        self._conn.execute(
            "UPDATE sessions SET status=?, updated_at=? WHERE session_id=?",
            ("approved" if decision == "approve" else "rejected", _now(), session_id),
        )
        self._conn.commit()


def _now() -> str:
    return datetime.utcnow().isoformat()
