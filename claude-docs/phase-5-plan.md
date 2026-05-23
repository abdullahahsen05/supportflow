# Phase 5 — Ollama + LangChain Minimal Chat Endpoint

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `POST /api/chat` endpoint that retrieves relevant KB chunks from ChromaDB, injects them into a prompt, calls `mistral:7b` via ChatOllama, and returns a grounded answer with source attribution.

**Architecture:** The endpoint is a thin orchestration layer: validate input → check Ollama availability via HTTP → retrieve chunks → build prompt → call LLM → return response. No persistence, no LangGraph, no tool calls. All LLM/prompt logic lives in `backend/app/llm/`; the router in `backend/app/api/chat.py` stays focused on HTTP concerns.

**Tech Stack:** FastAPI, LangChain (`langchain-ollama`, `langchain-core`), Ollama `mistral:7b`, ChromaDB retriever (already implemented), httpx for Ollama health check, Pydantic v2 for schemas.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/requirements.txt` | Add `langchain-core`, `httpx` |
| Create | `backend/app/llm/__init__.py` | Empty package marker |
| Create | `backend/app/llm/prompts.py` | System prompt, user template, `build_context()` |
| Create | `backend/app/llm/ollama.py` | `get_chat_llm()`, `check_ollama_available()` |
| Create | `backend/app/api/chat.py` | `POST /api/chat` router, request/response schemas |
| Create | `backend/app/llm/verify.py` | CLI smoke-test (`python -m app.llm.verify`) |
| Modify | `backend/app/main.py` | Register chat router |

---

## Task 1: Add dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add new deps to requirements.txt**

Replace the existing file content with:

```text
fastapi==0.115.12
uvicorn[standard]==0.34.3
pydantic==2.11.4
pydantic-settings==2.9.1
python-dotenv==1.1.0

# Database
sqlalchemy==2.0.41
psycopg[binary]==3.2.9
alembic==1.16.1

# RAG (Phase 4)
chromadb==0.6.3
langchain-text-splitters==0.3.8
langchain-ollama==0.3.3

# LLM (Phase 5)
langchain-core==0.3.62
httpx==0.28.1
```

- [ ] **Step 2: Install**

```powershell
cd C:\Users\Victus\Desktop\supportflow\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Expected: `Successfully installed` lines for `langchain-core` and `httpx` (or "already satisfied" if transitive deps already pulled them).

- [ ] **Step 3: Verify imports work**

```powershell
python -c "from langchain_ollama import ChatOllama; from langchain_core.messages import HumanMessage; import httpx; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```powershell
git add backend/requirements.txt
git commit -m "feat(phase5): add langchain-core and httpx dependencies"
```

---

## Task 2: Create `backend/app/llm/__init__.py`

**Files:**
- Create: `backend/app/llm/__init__.py`

- [ ] **Step 1: Create empty package marker**

Create `backend/app/llm/__init__.py` with empty content (the `.gitkeep` placeholder already exists in the folder; this replaces it as a proper Python package).

```python
```

*(Empty file — just needs to exist.)*

- [ ] **Step 2: Verify import**

```powershell
python -c "import app.llm; print('OK')"
```

Expected: `OK`

---

## Task 3: Create `backend/app/llm/prompts.py`

**Files:**
- Create: `backend/app/llm/prompts.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_prompts.py`:

```python
from __future__ import annotations

from app.llm.prompts import build_context


def test_build_context_empty():
    assert build_context([]) == ""


def test_build_context_single_chunk():
    chunks = [{"title": "Refund Policy", "text": "30-day refund window.", "source": "refund_policy.md"}]
    result = build_context(chunks)
    assert "[Source: Refund Policy]" in result
    assert "30-day refund window." in result


def test_build_context_multiple_chunks():
    chunks = [
        {"title": "Refund Policy", "text": "30-day window.", "source": "refund_policy.md"},
        {"title": "Shipping Policy", "text": "Ships in 3 days.", "source": "shipping_policy.md"},
    ]
    result = build_context(chunks)
    assert "---" in result
    assert "[Source: Refund Policy]" in result
    assert "[Source: Shipping Policy]" in result


def test_build_context_falls_back_to_source_when_no_title():
    chunks = [{"title": "", "source": "billing_policy.md", "text": "Billing info."}]
    result = build_context(chunks)
    assert "billing_policy.md" in result
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests/test_prompts.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` (prompts module doesn't exist yet).

- [ ] **Step 3: Create `backend/app/llm/prompts.py`**

```python
from __future__ import annotations

SYSTEM_PROMPT = (
    "You are a helpful customer support agent for CloudDesk Inc.\n"
    "Answer the customer's question using ONLY the context provided below.\n"
    "Do not invent policies, features, or facts not present in the context.\n"
    "If the context does not contain enough information, say so clearly and suggest "
    "the customer create a support ticket for further assistance.\n"
    "Be concise, friendly, and professional.\n"
    "When relevant, mention the source document name in your answer."
)

USER_TEMPLATE = (
    "Context from CloudDesk knowledge base:\n"
    "{context}\n\n"
    "Customer question: {question}\n\n"
    "Answer:"
)


def build_context(chunks: list[dict]) -> str:
    if not chunks:
        return ""
    parts = []
    for chunk in chunks:
        title = chunk.get("title") or chunk.get("source", "Unknown")
        parts.append(f"[Source: {title}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_prompts.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```powershell
git add backend/app/llm/prompts.py backend/tests/test_prompts.py
git commit -m "feat(phase5): add prompt templates and build_context helper"
```

---

## Task 4: Create `backend/app/llm/ollama.py`

**Files:**
- Create: `backend/app/llm/ollama.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_ollama_wrapper.py`:

```python
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.llm.ollama import check_ollama_available, get_chat_llm


def test_get_chat_llm_returns_chat_ollama():
    llm = get_chat_llm()
    assert llm is not None
    assert hasattr(llm, "ainvoke")


def test_check_ollama_available_connect_error():
    import httpx

    with patch("app.llm.ollama.httpx.get", side_effect=httpx.ConnectError("refused")):
        ok, reason = check_ollama_available()

    assert ok is False
    assert "not available" in reason.lower() or "ollama" in reason.lower()


def test_check_ollama_available_model_missing():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"models": [{"name": "llama3:8b"}]}

    with patch("app.llm.ollama.httpx.get", return_value=mock_resp):
        ok, reason = check_ollama_available()

    assert ok is False
    assert "ollama pull" in reason


def test_check_ollama_available_success():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"models": [{"name": "mistral:7b"}, {"name": "nomic-embed-text:latest"}]}

    with patch("app.llm.ollama.httpx.get", return_value=mock_resp):
        ok, reason = check_ollama_available()

    assert ok is True
    assert reason == ""
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests/test_ollama_wrapper.py -v
```

Expected: `ImportError` (module doesn't exist yet).

- [ ] **Step 3: Create `backend/app/llm/ollama.py`**

```python
from __future__ import annotations

import httpx
from langchain_ollama import ChatOllama

from app.core.config import settings


def get_chat_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.OLLAMA_CHAT_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.1,
        timeout=120,
    )


def check_ollama_available() -> tuple[bool, str]:
    """
    Returns (True, "") if Ollama is running and the configured chat model is available.
    Returns (False, human-readable reason) otherwise.
    """
    try:
        resp = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        resp.raise_for_status()
    except httpx.ConnectError:
        return False, (
            f"Ollama is not available at {settings.OLLAMA_BASE_URL}. "
            "Start Ollama and ensure mistral:7b is pulled."
        )
    except Exception as exc:
        return False, f"Ollama health check failed: {exc}"

    model = settings.OLLAMA_CHAT_MODEL
    model_names = [m.get("name", "") for m in resp.json().get("models", [])]
    if model not in model_names:
        return False, (
            f"Model '{model}' is not available in Ollama. "
            f"Run: ollama pull {model}"
        )
    return True, ""
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_ollama_wrapper.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```powershell
git add backend/app/llm/ollama.py backend/tests/test_ollama_wrapper.py
git commit -m "feat(phase5): add ChatOllama wrapper and availability check"
```

---

## Task 5: Create `backend/app/api/chat.py`

**Files:**
- Create: `backend/app/api/chat.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_chat_schemas.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.chat import ChatRequest


def test_chat_request_valid():
    req = ChatRequest(message="How do I cancel?")
    assert req.message == "How do I cancel?"
    assert req.k == 4


def test_chat_request_custom_k():
    req = ChatRequest(message="Hello", k=6)
    assert req.k == 6


def test_chat_request_empty_message_fails():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_k_too_large_fails():
    with pytest.raises(ValidationError):
        ChatRequest(message="Hello", k=99)


def test_chat_request_k_zero_fails():
    with pytest.raises(ValidationError):
        ChatRequest(message="Hello", k=0)
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests/test_chat_schemas.py -v
```

Expected: `ImportError` (module doesn't exist yet).

- [ ] **Step 3: Create `backend/app/api/chat.py`**

```python
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.config import settings
from app.llm.ollama import check_ollama_available, get_chat_llm
from app.llm.prompts import SYSTEM_PROMPT, USER_TEMPLATE, build_context
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, description="Customer question")]
    k: int = Field(default=4, ge=1, le=10, description="KB chunks to retrieve (1–10)")


class SourceInfo(BaseModel):
    title: str
    file_path: str
    chunk_index: int
    distance: float | None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    model: str


@router.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    ok, reason = check_ollama_available()
    if not ok:
        raise HTTPException(status_code=503, detail=reason)

    try:
        chunks = retrieve(request.message, k=request.k)
    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Retrieval error: {exc}")

    context = build_context(chunks)
    if not context:
        context = "No relevant information found in the knowledge base."

    user_content = USER_TEMPLATE.format(context=context, question=request.message)
    llm = get_chat_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]

    try:
        ai_message = await llm.ainvoke(messages)
        answer = ai_message.content if hasattr(ai_message, "content") else str(ai_message)
    except Exception as exc:
        logger.error("LLM invocation failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                f"Ollama is not available at {settings.OLLAMA_BASE_URL}. "
                f"Start Ollama and ensure {settings.OLLAMA_CHAT_MODEL} is pulled."
            ),
        )

    sources = [
        SourceInfo(
            title=c.get("title") or c.get("source", ""),
            file_path=c.get("file_path", ""),
            chunk_index=int(c.get("chunk_index", 0)),
            distance=c.get("distance"),
        )
        for c in chunks
    ]

    logger.info(
        "chat completed | model=%s | chunks=%d | answer_len=%d",
        settings.OLLAMA_CHAT_MODEL,
        len(chunks),
        len(answer),
    )

    return ChatResponse(answer=answer, sources=sources, model=settings.OLLAMA_CHAT_MODEL)
```

- [ ] **Step 4: Run schema tests to verify they pass**

```powershell
python -m pytest tests/test_chat_schemas.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/chat.py backend/tests/test_chat_schemas.py
git commit -m "feat(phase5): add POST /api/chat router with RAG + LLM pipeline"
```

---

## Task 6: Wire chat router into `main.py`

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add chat router import and registration**

In `backend/app/main.py`, add after the health router import/registration:

```python
    from app.api.chat import router as chat_router
    app.include_router(chat_router)
```

The full `create_app` function after the change:

```python
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Local-first agentic customer support platform.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.health import router as health_router
    app.include_router(health_router)

    from app.api.chat import router as chat_router
    app.include_router(chat_router)

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info(
            "SupportFlow API starting | env=%s | cors=%s",
            settings.APP_ENV,
            settings.BACKEND_CORS_ORIGINS,
        )

    return app
```

- [ ] **Step 2: Verify the app imports cleanly**

```powershell
python -c "from app.main import app; print('routes:', [r.path for r in app.routes])"
```

Expected output includes `/health` and `/api/chat`.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/main.py
git commit -m "feat(phase5): register /api/chat router in app factory"
```

---

## Task 7: Create `backend/app/llm/verify.py` (CLI smoke-test)

**Files:**
- Create: `backend/app/llm/verify.py`

- [ ] **Step 1: Create the script**

```python
"""
CLI smoke-test for the Phase 5 Ollama + RAG pipeline.

Usage (from backend/ with .venv active):
    python -m app.llm.verify "What is your refund period?"
"""
from __future__ import annotations

import asyncio
import sys


def _safe(text: str) -> str:
    enc = sys.stdout.encoding or "utf-8"
    return text.encode(enc, errors="replace").decode(enc)


async def _run(query: str) -> None:
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.llm.ollama import check_ollama_available, get_chat_llm
    from app.llm.prompts import SYSTEM_PROMPT, USER_TEMPLATE, build_context
    from app.rag.retriever import retrieve

    print(_safe(f'\nQuery: "{query}"'))
    print("=" * 60)

    ok, reason = check_ollama_available()
    if not ok:
        print(f"ERROR: {reason}")
        sys.exit(1)
    print("Ollama: available")

    chunks = retrieve(query, k=4)
    print(f"Retrieved {len(chunks)} chunks:")
    for i, c in enumerate(chunks, 1):
        print(f"  [{i}] {c['title']}  (distance={c['distance']})")

    context = build_context(chunks)
    if not context:
        context = "No relevant information found in the knowledge base."

    user_content = USER_TEMPLATE.format(context=context, question=query)
    llm = get_chat_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]

    print("\nCalling LLM (may take 30–60 s on first call)...")
    ai_message = await llm.ainvoke(messages)
    answer = ai_message.content if hasattr(ai_message, "content") else str(ai_message)

    print("\nAnswer:")
    print("-" * 60)
    print(_safe(answer))


if __name__ == "__main__":
    _query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is your refund period?"
    asyncio.run(_run(_query))
```

- [ ] **Step 2: Commit**

```powershell
git add backend/app/llm/verify.py
git commit -m "feat(phase5): add CLI smoke-test script for LLM + RAG pipeline"
```

---

## Task 8: Run all unit tests together

- [ ] **Step 1: Run full test suite**

```powershell
python -m pytest tests/test_prompts.py tests/test_ollama_wrapper.py tests/test_chat_schemas.py -v
```

Expected: `13 passed` (4 + 4 + 5)

---

## Task 9: Manual verification (requires Ollama running)

Follow the exact checklist below. Paste terminal output before claiming Phase 5 complete.

**Prerequisites:**
```powershell
# Terminal 1 — ensure Ollama is running
ollama list   # must show mistral:7b

# Terminal 2 — from repo root
docker compose up -d postgres

# Terminal 3 — backend
cd C:\Users\Victus\Desktop\supportflow\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

- [ ] **Check 1: CLI smoke-test (subscription)**

```powershell
python -m app.llm.verify "How do I cancel my subscription?"
```

Expected: Answer mentions cancellation at end of billing period + sources include `subscription_policy.md`.

- [ ] **Check 2: CLI smoke-test (refund)**

```powershell
python -m app.llm.verify "What is your refund period?"
```

Expected: Answer mentions 14 days + sources include `refund_policy.md`.

- [ ] **Check 3: CLI smoke-test (unknown question)**

```powershell
python -m app.llm.verify "What is CloudDesk's policy on alien spaceship rentals?"
```

Expected: Answer says it doesn't have information; does NOT invent a policy.

- [ ] **Check 4: Swagger — subscription question**

Open `http://localhost:8000/docs` → `POST /api/chat`:
```json
{"message": "How do I cancel my subscription?", "k": 4}
```
Expected: 200 with `answer` + `sources` array + `model: "mistral:7b"`.

- [ ] **Check 5: Swagger — refund question**

```json
{"message": "What is your refund period?", "k": 4}
```
Expected: Answer mentions 14 days + `sources` includes `refund_policy.md`.

- [ ] **Check 6: Swagger — empty message validation**

```json
{"message": ""}
```
Expected: 422 Unprocessable Entity.

- [ ] **Check 7: Health still works**

`GET /health` → 200 `{"status": "ok", ...}`

- [ ] **Check 8: Ollama unavailable path**

Stop Ollama (`Ctrl+C` in Ollama terminal or `taskkill /F /IM ollama.exe`), then:
```json
{"message": "How do I cancel?", "k": 4}
```
Expected: 503 with `{"detail": "Ollama is not available at http://localhost:11434..."}`.
Restart Ollama after.

---

## Spec Coverage Self-Review

| Requirement | Covered by |
|-------------|-----------|
| `POST /api/chat` with `message` + `k` | Task 5 — `ChatRequest` |
| Response: `answer`, `sources`, `model` | Task 5 — `ChatResponse` / `SourceInfo` |
| Sources include title, file_path, chunk_index, distance | Task 5 — `SourceInfo` |
| Empty message → 422 | Task 5 — `Field(min_length=1)` |
| No relevant context → honest answer | Task 3 — SYSTEM_PROMPT instructs honesty |
| Prompt: grounded in context, no invented policies | Task 3 — `SYSTEM_PROMPT` |
| Ollama down → 503 friendly JSON | Task 4 — `check_ollama_available()`, Task 5 — `HTTPException(503)` |
| Model missing → friendly error with `ollama pull` | Task 4 — `check_ollama_available()` |
| `GET /health` continues to work | Task 6 — existing router untouched |
| Swagger shows `POST /api/chat` | Task 6 — router registered with tags |
| `python -m app.llm.verify` smoke-test | Task 7 |
| No persistence, no LangGraph, no tools | Nothing added — scope kept minimal |
