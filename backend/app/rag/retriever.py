"""
Retrieve relevant knowledge base chunks for a query.

Usage (from backend/ with .venv active):
    python -m app.rag.retriever "your query here"

Importable:
    from app.rag.retriever import retrieve
    results = retrieve("refund period", k=4)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import chromadb
from langchain_ollama import OllamaEmbeddings

# ── Paths ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHROMA_DIR = REPO_ROOT / "data" / "chroma"

from app.core.config import settings

COLLECTION_NAME = "supportflow_knowledge_base"


# ── Public API ─────────────────────────────────────────────────────────────

def retrieve(query: str, k: int = 4) -> list[dict[str, Any]]:
    """
    Return top-k relevant chunks for *query*.

    Each result dict contains:
        text       - the chunk text
        source     - document title
        title      - document title
        file_path  - repo-root-relative path
        chunk_index - position within the source document
        distance   - ChromaDB L2 distance (lower = more similar)
    """
    embedder = OllamaEmbeddings(
        model=settings.OLLAMA_EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        raise RuntimeError(
            f"ChromaDB collection '{COLLECTION_NAME}' not found at {CHROMA_DIR}.\n"
            "Run: python -m app.rag.ingest"
        )

    total = collection.count()
    if total == 0:
        return []

    query_vector = embedder.embed_query(query)
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(k, total),
        include=["documents", "metadatas", "distances"],
    )

    docs   = results.get("documents", [[]])[0]
    metas  = results.get("metadatas",  [[]])[0]
    dists  = results.get("distances",  [[]])[0]

    return [
        {
            "text":        docs[i],
            "source":      metas[i].get("source", ""),
            "title":       metas[i].get("title", ""),
            "file_path":   metas[i].get("file_path", ""),
            "chunk_index": metas[i].get("chunk_index", 0),
            "distance":    round(dists[i], 4) if dists else None,
        }
        for i in range(len(docs))
    ]


# ── CLI verification ───────────────────────────────────────────────────────

def _safe_print(text: str) -> None:
    """Print text safely on Windows consoles with limited encoding (e.g. cp1252)."""
    encoded = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8"
    )
    print(encoded)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "refund policy"

    _safe_print(f'\nQuery: "{query}"')
    _safe_print("=" * 60)

    try:
        hits = retrieve(query, k=3)
    except RuntimeError as e:
        _safe_print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        _safe_print(f"ERROR: {e}")
        _safe_print("Is Ollama running? Have you run: python -m app.rag.ingest ?")
        sys.exit(1)

    if not hits:
        _safe_print("No results found.")
    else:
        for i, hit in enumerate(hits, 1):
            _safe_print(f"\n[{i}] {hit['title']}  (distance={hit['distance']})")
            _safe_print(f"    file      : {hit['file_path']}")
            _safe_print(f"    chunk     : #{hit['chunk_index']}")
            preview = hit["text"][:300].replace("\n", " ")
            _safe_print(f"    preview   : {preview}...")
