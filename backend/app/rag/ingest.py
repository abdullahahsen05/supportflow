"""
Ingest knowledge base documents into ChromaDB.

Usage (from backend/ with .venv active):
    python -m app.rag.ingest

Idempotent: chunks are upserted with stable IDs — safe to run multiple times.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import chromadb
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── Paths ──────────────────────────────────────────────────────────────────
# ingest.py: backend/app/rag/ingest.py  →  repo root is 4 levels up
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHROMA_DIR = REPO_ROOT / "data" / "chroma"

# ── App imports (work when run via `python -m app.rag.ingest` from backend/) ─
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.knowledge_document import KnowledgeDocument

COLLECTION_NAME = "supportflow_knowledge_base"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


# ── Ollama health check ────────────────────────────────────────────────────

def check_ollama() -> None:
    """Exit with a clear message if Ollama or the embed model is unavailable."""
    url = f"{settings.OLLAMA_BASE_URL}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except Exception:
        print(f"\nERROR: Ollama is not available at {settings.OLLAMA_BASE_URL}")
        print("  Start Ollama: ollama serve")
        sys.exit(1)

    model = settings.OLLAMA_EMBED_MODEL
    installed = [m.get("name", "") for m in data.get("models", [])]
    if not any(model in name for name in installed):
        print(f"\nERROR: Embedding model '{model}' not found in Ollama.")
        print(f"  Run: ollama pull {model}")
        sys.exit(1)

    print(f"[OK] Ollama reachable  |  model '{model}' ready")


# ── ChromaDB ───────────────────────────────────────────────────────────────

def get_collection() -> chromadb.Collection:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME)


# ── Main ingestion ─────────────────────────────────────────────────────────

def ingest() -> None:
    print("SupportFlow AI -- RAG Ingestion")
    print("=" * 50)

    check_ollama()

    embedder = OllamaEmbeddings(
        model=settings.OLLAMA_EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    collection = get_collection()

    db = SessionLocal()
    try:
        docs = db.query(KnowledgeDocument).all()
        print(f"\nDocuments found in DB: {len(docs)}")
        print("-" * 50)

        total_chunks = 0
        for doc in docs:
            abs_path = REPO_ROOT / doc.file_path
            if not abs_path.exists():
                print(f"[WARN] File not found, skipping: {abs_path}")
                continue

            text = abs_path.read_text(encoding="utf-8")
            chunks = splitter.split_text(text)
            if not chunks:
                print(f"[WARN] No content in {doc.title}, skipping")
                continue

            # Stable chunk IDs: upsert keeps this idempotent
            ids = [f"doc_{doc.id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "document_id": str(doc.id),
                    "title": doc.title,
                    "source": doc.title,
                    "file_path": doc.file_path,
                    "chunk_index": i,
                }
                for i in range(len(chunks))
            ]

            print(f"  [{doc.id:2d}] {doc.title:<25s} {len(chunks)} chunks ... ", end="", flush=True)
            vectors = embedder.embed_documents(chunks)
            collection.upsert(ids=ids, embeddings=vectors, documents=chunks, metadatas=metadatas)

            doc.indexed = True
            db.add(doc)
            total_chunks += len(chunks)
            print("done")

        db.commit()
        print(f"\n[OK] Ingestion complete.")
        print(f"  Collection : {COLLECTION_NAME}")
        print(f"  Documents  : {len(docs)}")
        print(f"  Chunks     : {total_chunks}")
        print(f"  Chroma dir : {CHROMA_DIR}")
        print(f"  Total in DB: {collection.count()} chunks")

    except Exception:
        db.rollback()
        print("\n[FAIL] Ingestion failed -- DB transaction rolled back.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ingest()
