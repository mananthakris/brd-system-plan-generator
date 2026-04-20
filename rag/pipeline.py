"""RAG pipeline: Chroma vector store + OpenAI text-embedding-3-small.

Source types stored in Chroma metadata:
  architecture_decision | current_stack | team_skills | cloud_infrastructure |
  past_brd | plan_template | domain_context | eng_standards
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from config import settings
from schemas.models import RAGContext


SOURCE_TYPES = {
    "architecture_decision",
    "current_stack",
    "team_skills",
    "cloud_infrastructure",
    "past_brd",
    "plan_template",
    "domain_context",
    "eng_standards",
}

# Map source directory file prefixes → source_type
_FILE_PREFIX_MAP = {
    "architecture": "architecture_decision",
    "current_tools": "current_stack",
    "team_skills": "team_skills",
    "cloud": "cloud_infrastructure",
    "brd_": "past_brd",
    "prd_": "past_brd",
    "plan_template": "plan_template",
    "eng_standards": "eng_standards",
    "domain": "domain_context",
}


class RAGPipeline:
    def __init__(self, persist_dir: str | None = None):
        persist_dir = persist_dir or settings.chroma_persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._embed_fn = OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name=settings.embedding_model,
        )
        self._collection = self._client.get_or_create_collection(
            name="verdant_knowledge",
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_documents(
        self,
        texts: list[str],
        source_type: str,
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"Unknown source_type '{source_type}'. Valid: {SOURCE_TYPES}")

        n = len(texts)
        _ids = ids or [str(uuid.uuid4()) for _ in range(n)]
        _metas = metadatas or [{} for _ in range(n)]

        for m in _metas:
            m["source_type"] = source_type

        self._collection.upsert(documents=texts, metadatas=_metas, ids=_ids)

    def add_document(self, text: str, source_type: str, metadata: dict | None = None) -> str:
        doc_id = str(uuid.uuid4())
        self.add_documents([text], source_type, [metadata or {}], [doc_id])
        return doc_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        n_results: int | None = None,
        source_types: Optional[list[str]] = None,
    ) -> RAGContext:
        n = n_results or settings.rag_top_k
        where = (
            {"source_type": {"$in": source_types}}
            if source_types and len(source_types) > 0
            else None
        )

        kwargs: dict = {"query_texts": [query], "n_results": n}
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results.get("distances") else []

        # Chroma cosine distance → similarity score
        scores = [round(1.0 - d, 4) for d in distances]

        # Filter below threshold
        threshold = settings.rag_score_threshold
        filtered = [
            (doc, meta, score)
            for doc, meta, score in zip(docs, metas, scores)
            if score >= threshold
        ]

        if filtered:
            docs, metas, scores = zip(*filtered)
            docs, metas, scores = list(docs), list(metas), list(scores)
        else:
            docs, metas, scores = [], [], []

        sources = [m.get("source_file", m.get("source_type", "unknown")) for m in metas]

        return RAGContext(
            query=query,
            retrieved_chunks=docs,
            sources=sources,
            scores=scores,
        )

    def count(self) -> int:
        return self._collection.count()

    # ------------------------------------------------------------------
    # Seed from directory
    # ------------------------------------------------------------------

    def seed_from_directory(self, sources_dir: str | Path) -> int:
        """
        Load all .md and .txt files from sources_dir into Chroma.
        Infers source_type from filename prefix (see _FILE_PREFIX_MAP).
        Returns number of chunks added.
        """
        sources_dir = Path(sources_dir)
        added = 0

        for fpath in sorted(sources_dir.glob("*.md")) + sorted(sources_dir.glob("*.txt")):  # type: ignore[operator]
            source_type = _infer_source_type(fpath.name)
            chunks = _chunk_markdown(fpath.read_text(encoding="utf-8"))

            metas = [{"source_file": fpath.name, "chunk_index": i} for i in range(len(chunks))]
            ids = [f"{fpath.stem}_chunk_{i}" for i in range(len(chunks))]

            self.add_documents(chunks, source_type, metas, ids)
            added += len(chunks)
            print(f"  seeded {fpath.name} → {len(chunks)} chunks [{source_type}]")

        return added


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_source_type(filename: str) -> str:
    lower = filename.lower()
    for prefix, stype in _FILE_PREFIX_MAP.items():
        if lower.startswith(prefix):
            return stype
    return "domain_context"


def _chunk_markdown(text: str, max_chars: int = 1200, overlap: int = 100) -> list[str]:
    """Split on double-newlines first, then hard-chunk oversized blocks."""
    raw_blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    chunks: list[str] = []
    buffer = ""

    for block in raw_blocks:
        if len(buffer) + len(block) + 2 <= max_chars:
            buffer = f"{buffer}\n\n{block}".strip()
        else:
            if buffer:
                chunks.append(buffer)
            if len(block) > max_chars:
                # Hard split with overlap
                for i in range(0, len(block), max_chars - overlap):
                    chunks.append(block[i : i + max_chars])
                buffer = ""
            else:
                buffer = block

    if buffer:
        chunks.append(buffer)

    return chunks
