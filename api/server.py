"""FastAPI application entry point.

Startup: seeds the RAG knowledge base (idempotent) and initialises the
shared RAG pipeline instance used by all pipeline runs.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.run import router as run_router
from api.routes.stream import router as stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed RAG once at startup — Chroma upserts are idempotent
    from rag.seed import seed as seed_rag
    from api.session import init_rag

    print("Seeding RAG knowledge base...")
    seed_rag()
    init_rag()
    print("RAG ready.")
    yield


app = FastAPI(title="Arbor Risk — Engineering Plan API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(run_router, prefix="/api")
app.include_router(stream_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
