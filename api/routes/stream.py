"""GET /api/stream/{session_id} — SSE stream of pipeline events."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.session import get_session

router = APIRouter()

_TERMINAL_TYPES = {"pipeline_complete", "pipeline_rejected", "error"}
_QUEUE_TIMEOUT_S = 120  # seconds before we give up waiting for the next event


@router.get("/stream/{session_id}")
async def stream_pipeline(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    return StreamingResponse(
        _event_generator(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _event_generator(session_id: str) -> AsyncIterator[str]:
    session = get_session(session_id)
    if not session:
        yield _sse({"type": "error", "message": "session not found"})
        return

    loop = asyncio.get_running_loop()

    while True:
        q = session.events  # capture reference outside lambda
        try:
            # Pull from the sync queue without blocking the event loop
            event = await loop.run_in_executor(
                None, lambda: q.get(timeout=_QUEUE_TIMEOUT_S)
            )
        except Exception:
            yield _sse({"type": "error", "message": "stream timeout"})
            return

        yield _sse(event)

        if event.get("type") in _TERMINAL_TYPES:
            return


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
