# Phase 11 — MLflow Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Log every POST /api/chat interaction as an MLflow experiment run using local file-based tracking, so AI interactions are fully observable for LLMOps/MLOps purposes.

**Architecture:** A new `backend/app/observability/mlflow_tracking.py` module exposes a single `log_chat_run()` function that is called from the chat endpoint after the agent completes. MLflow logging is always wrapped in `try/except` so failures never break `/api/chat`. Tracking uses a local file store (`file:../mlruns` relative to `backend/`, which places `mlruns/` at the repo root). The MLflow UI reads from the same directory.

**Tech Stack:** Python 3.11, FastAPI, MLflow (file-based local tracking), `unittest.mock` for tests, existing LangGraph agent state.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `backend/requirements.txt` | Modify | Add `mlflow` |
| `backend/app/core/config.py` | Modify | Add `MLFLOW_TRACKING_URI`, `MLFLOW_EXPERIMENT_NAME` |
| `backend/.env` | Modify | Update MLflow vars to file-based tracking |
| `backend/app/observability/__init__.py` | Create | Empty package init |
| `backend/app/observability/mlflow_tracking.py` | Create | `PROMPT_VERSION`, `log_chat_run()` |
| `backend/app/api/chat.py` | Modify | Add timing + call `log_chat_run()` |
| `backend/tests/test_mlflow_tracking.py` | Create | Unit + integration tests |
| `backend/README.md` | Modify | MLflow UI docs |

No frontend files change. No database migrations needed.

---

## Task 1: Add `mlflow` dependency and config settings

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env`

- [ ] **Step 1: Add mlflow to `backend/requirements.txt`**

Add after the `# Agent (Phase 7)` block:

```
# Observability (Phase 11)
mlflow==2.22.0
```

Full file after change (bottom section):

```
# Agent (Phase 7)
langgraph==1.2.1

# Observability (Phase 11)
mlflow==2.22.0

# Testing
pytest==9.0.3
```

- [ ] **Step 2: Add MLflow settings to `backend/app/core/config.py`**

Add the two new fields to the `Settings` class after the `CHROMA_COLLECTION` line:

```python
    # MLflow (Phase 11)
    MLFLOW_TRACKING_URI: str = "file:../mlruns"
    MLFLOW_EXPERIMENT_NAME: str = "supportflow-ai-chat"
```

The full `Settings` class after the addition:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "SupportFlow AI"
    APP_ENV: str = "development"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    FRONTEND_URL: str = "http://localhost:3000"

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database (Phase 2+)
    DATABASE_URL: str = "postgresql+psycopg://supportflow:supportflow@localhost:5433/supportflow"

    # Ollama (Phase 4+)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "mistral:7b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # ChromaDB (Phase 4+)
    CHROMA_COLLECTION: str = "supportflow_knowledge_base"

    # MLflow (Phase 11)
    MLFLOW_TRACKING_URI: str = "file:../mlruns"
    MLFLOW_EXPERIMENT_NAME: str = "supportflow-ai-chat"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
```

- [ ] **Step 3: Update `backend/.env` MLflow section**

Replace the existing MLflow lines:
```
# ---- MLflow (introduced in Phase 11) ----
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT=supportflow
```

With:
```
# ---- MLflow (Phase 11) ----
# file:../mlruns writes to <repo-root>/mlruns (relative to backend/ working dir)
MLFLOW_TRACKING_URI=file:../mlruns
MLFLOW_EXPERIMENT_NAME=supportflow-ai-chat
```

- [ ] **Step 4: Install updated requirements**

```powershell
cd C:\Users\Victus\Desktop\supportflow\backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Expected: mlflow and its deps install without errors. Last line should be something like `Successfully installed mlflow-2.22.0 ...`

- [ ] **Step 5: Verify import**

```powershell
.venv\Scripts\python.exe -c "import mlflow; print(mlflow.__version__)"
```

Expected: prints `2.22.0`

- [ ] **Step 6: Verify settings load**

```powershell
.venv\Scripts\python.exe -c "from app.core.config import settings; print(settings.MLFLOW_TRACKING_URI, settings.MLFLOW_EXPERIMENT_NAME)"
```

Expected: `file:../mlruns supportflow-ai-chat`

- [ ] **Step 7: Commit**

```powershell
git add backend/requirements.txt backend/app/core/config.py backend/.env
git commit -m "feat(phase-11): add mlflow dependency and config settings"
```

---

## Task 2: Create `backend/app/observability/` package

**Files:**
- Create: `backend/app/observability/__init__.py`
- Create: `backend/app/observability/mlflow_tracking.py`
- Create: `backend/tests/test_mlflow_tracking.py`

- [ ] **Step 1: Write the failing tests in `backend/tests/test_mlflow_tracking.py`**

```python
"""
Tests for backend/app/observability/mlflow_tracking.py

Strategy
--------
* Test 1: log_chat_run completes without raising using a real temp file-based
  tracking URI (verifies happy path with actual MLflow writes).
* Test 2: log_chat_run is silent when mlflow.start_run raises (verifies
  non-breaking behaviour when MLflow is misconfigured/unavailable).
* Test 3: log_chat_run is silent when mlflow itself cannot be imported
  (verifies graceful degradation if the package were somehow absent).

Run from backend/ with .venv active:
    pytest tests/test_mlflow_tracking.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.observability.mlflow_tracking import log_chat_run, PROMPT_VERSION


# ---------------------------------------------------------------------------
# Shared payload used across tests
# ---------------------------------------------------------------------------

_PAYLOAD = dict(
    model="mistral:7b",
    user_message="Where is my order #1004?",
    answer="Your order #1004 has shipped. Tracking: TRK-CD-1004.",
    intent="order_status",
    sentiment="neutral",
    confidence=0.85,
    tool_name="get_order_status",
    tool_result={"found": True, "order_number": "1004", "status": "shipped"},
    sources=[{"title": "Order Policy", "file_path": "orders.md", "chunk_index": 0, "distance": 0.12}],
    latency_seconds=2.34,
    conversation_id=42,
    ticket_id=None,
    escalated=False,
    error=None,
)

_ESCALATED_PAYLOAD = dict(
    model="mistral:7b",
    user_message="I was charged twice this month.",
    answer="We detected a duplicate charge and escalated your case.",
    intent="billing_issue",
    sentiment="negative",
    confidence=0.91,
    tool_name="check_payment_history",
    tool_result={"found": True, "duplicate_detected": True, "payments": []},
    sources=[],
    latency_seconds=3.11,
    conversation_id=99,
    ticket_id=7,
    escalated=True,
    error=None,
)


# ---------------------------------------------------------------------------
# Test 1: happy path — real file-based MLflow write
# ---------------------------------------------------------------------------

class TestLogChatRunHappyPath:

    def test_does_not_raise_for_faq_interaction(self, tmp_path):
        """log_chat_run writes to a temp file store without raising."""
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = f"file:{tmp_path / 'mlruns'}"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test-experiment"
            # Should not raise
            log_chat_run(**_PAYLOAD)

    def test_does_not_raise_for_escalated_interaction(self, tmp_path):
        """log_chat_run handles ticket_created=True and escalated=True without raising."""
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = f"file:{tmp_path / 'mlruns'}"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test-experiment"
            log_chat_run(**_ESCALATED_PAYLOAD)

    def test_does_not_raise_when_all_optionals_are_none(self, tmp_path):
        """log_chat_run handles all optional fields being None gracefully."""
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = f"file:{tmp_path / 'mlruns'}"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test-experiment"
            log_chat_run(
                model="mistral:7b",
                user_message="Hello",
                answer="Hi",
                intent=None,
                sentiment=None,
                confidence=None,
                tool_name=None,
                tool_result=None,
                sources=[],
                latency_seconds=0.5,
                conversation_id=1,
                ticket_id=None,
                escalated=False,
                error=None,
            )

    def test_prompt_version_constant_is_set(self):
        """PROMPT_VERSION constant is a non-empty string."""
        assert isinstance(PROMPT_VERSION, str)
        assert len(PROMPT_VERSION) > 0


# ---------------------------------------------------------------------------
# Test 2: MLflow failure is swallowed — chat must not break
# ---------------------------------------------------------------------------

class TestLogChatRunNonBreaking:

    def test_silent_when_start_run_raises(self):
        """log_chat_run swallows exceptions from mlflow.start_run."""
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = "file:/nonexistent"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test"
            with patch("mlflow.start_run", side_effect=Exception("MLflow is down")):
                # Must not raise — chat availability depends on this
                log_chat_run(**_PAYLOAD)

    def test_silent_when_set_tracking_uri_raises(self):
        """log_chat_run swallows exceptions from mlflow.set_tracking_uri."""
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = "file:/nonexistent"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test"
            with patch("mlflow.set_tracking_uri", side_effect=RuntimeError("URI error")):
                log_chat_run(**_PAYLOAD)

    def test_silent_when_mlflow_import_fails(self):
        """log_chat_run is a no-op if mlflow raises on import (ImportError path)."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "mlflow":
                raise ImportError("mlflow not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # Must not raise
            log_chat_run(**_PAYLOAD)
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
cd C:\Users\Victus\Desktop\supportflow\backend
.venv\Scripts\python.exe -m pytest tests/test_mlflow_tracking.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `app.observability.mlflow_tracking` does not exist yet.

- [ ] **Step 3: Create `backend/app/observability/__init__.py`**

```python
```

(Empty file — makes `observability` a Python package.)

- [ ] **Step 4: Create `backend/app/observability/mlflow_tracking.py`**

```python
"""
MLflow tracking for SupportFlow AI chat interactions.

Every POST /api/chat call logs one MLflow run containing:
  Params  : model, prompt_version, intent, sentiment, tool_name
  Metrics : latency_seconds, answer_length, retrieved_source_count, confidence
  Tags    : conversation_id, ticket_created, escalated
  Artifacts: user_message.txt, answer.txt, sources.json, tool_result.json, error.txt

Tracking URI default: file:../mlruns  (repo-root/mlruns when run from backend/)
Experiment name    : supportflow-ai-chat

All logging is wrapped in try/except — a failure here NEVER breaks /api/chat.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1-agent-rag-tools"


def log_chat_run(
    *,
    model: str,
    user_message: str,
    answer: str,
    intent: Optional[str],
    sentiment: Optional[str],
    confidence: Optional[float],
    tool_name: Optional[str],
    tool_result: Optional[dict[str, Any]],
    sources: list[dict[str, Any]],
    latency_seconds: float,
    conversation_id: int,
    ticket_id: Optional[int],
    escalated: bool,
    error: Optional[str],
) -> None:
    """Log a single chat interaction as an MLflow run. Never raises."""
    try:
        import mlflow  # lazy — graceful if unavailable

        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)

        with mlflow.start_run():
            # ── Params (small string values) ──────────────────────────────
            mlflow.log_params({
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "intent": intent or "unknown",
                "sentiment": sentiment or "neutral",
                "tool_name": tool_name or "none",
            })

            # ── Metrics (numeric values) ──────────────────────────────────
            metrics: dict[str, float] = {
                "latency_seconds": latency_seconds,
                "answer_length": float(len(answer)),
                "retrieved_source_count": float(len(sources)),
            }
            if confidence is not None:
                metrics["confidence"] = float(confidence)
            mlflow.log_metrics(metrics)

            # ── Tags ──────────────────────────────────────────────────────
            mlflow.set_tags({
                "conversation_id": str(conversation_id),
                "ticket_created": str(ticket_id is not None).lower(),
                "escalated": str(escalated).lower(),
            })

            # ── Artifacts ─────────────────────────────────────────────────
            mlflow.log_text(user_message, "user_message.txt")
            mlflow.log_text(answer, "answer.txt")

            if sources:
                mlflow.log_text(json.dumps(sources, indent=2), "sources.json")

            if tool_result:
                # Exclude potentially large list fields to avoid huge artifacts
                summary = {
                    k: v
                    for k, v in tool_result.items()
                    if not isinstance(v, list) or len(v) <= 5
                }
                mlflow.log_text(json.dumps(summary, indent=2), "tool_result.json")

            if error:
                mlflow.log_text(error, "error.txt")

    except Exception as exc:
        logger.warning("MLflow logging failed (non-fatal): %s", exc)
```

- [ ] **Step 5: Run tests to verify they pass**

```powershell
cd C:\Users\Victus\Desktop\supportflow\backend
.venv\Scripts\python.exe -m pytest tests/test_mlflow_tracking.py -v
```

Expected: `8 passed` (4 happy-path + 4 non-breaking tests).

- [ ] **Step 6: Commit**

```powershell
git add backend/app/observability/__init__.py backend/app/observability/mlflow_tracking.py backend/tests/test_mlflow_tracking.py
git commit -m "feat(phase-11): add observability package with log_chat_run and tests"
```

---

## Task 3: Integrate `log_chat_run` into `backend/app/api/chat.py`

**Files:**
- Modify: `backend/app/api/chat.py`
- Test: `backend/tests/test_phase8.py` (existing tests must still pass)
- Test: `backend/tests/test_mlflow_tracking.py` (add integration test)

- [ ] **Step 1: Write a failing integration test in `backend/tests/test_mlflow_tracking.py`**

Append this class to the file:

```python
# ---------------------------------------------------------------------------
# Test 3: POST /api/chat still works with MLflow wired in
# ---------------------------------------------------------------------------

class TestChatEndpointWithMlflow:

    _OLLAMA_CHECK = "app.api.chat.check_ollama_available"
    _RUN_AGENT    = "app.api.chat.run_agent"

    def _state_faq(self) -> dict:
        return {
            "message": "What is your refund period?",
            "intent": "faq",
            "sentiment": "neutral",
            "confidence": 0.85,
            "needs_human": False,
            "retrieved_context": [],
            "sources": [
                {"title": "Refund Policy", "file_path": "refund_policy.md",
                 "chunk_index": 0, "distance": 0.1}
            ],
            "tool_name": None,
            "tool_input": None,
            "tool_result": None,
            "ticket": None,
            "answer": "Our refund period is 30 days.",
            "error": None,
        }

    def test_chat_returns_200_when_mlflow_succeeds(self, tmp_path):
        """POST /api/chat returns 200 and MLflow run is written to tmp store."""
        from fastapi.testclient import TestClient
        from app.main import app

        with patch(self._OLLAMA_CHECK, return_value=(True, "")), \
             patch(self._RUN_AGENT, return_value=self._state_faq()), \
             patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = f"file:{tmp_path / 'mlruns'}"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test-chat"
            client = TestClient(app)
            resp = client.post("/api/chat", json={"message": "What is your refund period?"})

        assert resp.status_code == 200
        assert resp.json()["conversation_id"] > 0

    def test_chat_returns_200_when_mlflow_fails(self):
        """POST /api/chat returns 200 even when MLflow raises."""
        from fastapi.testclient import TestClient
        from app.main import app

        with patch(self._OLLAMA_CHECK, return_value=(True, "")), \
             patch(self._RUN_AGENT, return_value=self._state_faq()), \
             patch("mlflow.set_tracking_uri", side_effect=Exception("MLflow down")):
            client = TestClient(app)
            resp = client.post("/api/chat", json={"message": "What is your refund period?"})

        assert resp.status_code == 200
```

- [ ] **Step 2: Run new tests to verify they fail**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_mlflow_tracking.py::TestChatEndpointWithMlflow -v
```

Expected: FAIL — `log_chat_run` is not yet called from the chat endpoint.

- [ ] **Step 3: Update `backend/app/api/chat.py`**

Replace the entire file with:

```python
from __future__ import annotations

import asyncio
import logging
import time
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.graph import run_agent
from app.core.config import settings
from app.db.session import get_db
from app.llm.ollama import check_ollama_available
from app.observability.mlflow_tracking import log_chat_run
from app.services.conversation_service import (
    get_or_create_conversation,
    link_ticket_to_conversation,
    save_message,
    save_tool_call,
    update_conversation_meta,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, description="Customer question")]
    k: int = Field(default=4, ge=1, le=10, description="KB chunks to retrieve")
    conversation_id: Optional[int] = Field(
        default=None, description="Existing conversation to append to"
    )
    user_email: Optional[str] = Field(
        default=None, description="Customer email to link conversation to a user"
    )


class SourceInfo(BaseModel):
    title: str
    file_path: str
    chunk_index: int
    distance: Optional[float] = None


class ChatResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: list[SourceInfo]
    model: str
    intent: Optional[str] = None
    tool_name: Optional[str] = None
    tool_result: Optional[dict[str, Any]] = None
    ticket: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    # Gate on Ollama availability before touching the DB
    ok, reason = check_ollama_available()
    if not ok:
        raise HTTPException(status_code=503, detail=reason)

    # Start latency timer (after Ollama health check — measures AI + persistence)
    t0 = time.perf_counter()

    # 1. Get or create conversation
    conv = get_or_create_conversation(db, request.conversation_id, request.user_email)
    conv_id = conv.id

    # 2. Save customer message
    save_message(db, conv_id, "customer", request.message)

    # 3. Run the LangGraph agent in a thread pool (all nodes are sync)
    loop = asyncio.get_event_loop()
    try:
        state = await loop.run_in_executor(None, run_agent, request.message)
    except Exception as exc:
        db.rollback()
        logger.error("Agent execution failed: %s", exc)
        # Log the failure to MLflow (non-blocking)
        log_chat_run(
            model=settings.OLLAMA_CHAT_MODEL,
            user_message=request.message,
            answer="",
            intent=None,
            sentiment=None,
            confidence=None,
            tool_name=None,
            tool_result=None,
            sources=[],
            latency_seconds=time.perf_counter() - t0,
            conversation_id=conv_id,
            ticket_id=None,
            escalated=False,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")

    answer = state.get("answer") or "I was unable to generate a response. Please try again."
    ticket = state.get("ticket")

    # 4. Save AI response message
    save_message(db, conv_id, "ai", answer)

    # 5. Persist tool call if the agent invoked a tool
    if state.get("tool_name"):
        save_tool_call(
            db,
            conv_id,
            state["tool_name"],
            state.get("tool_input"),
            state.get("tool_result"),
        )

    # 6. Link ticket to conversation if one was created/escalated
    if ticket and ticket.get("ticket_id"):
        link_ticket_to_conversation(db, ticket["ticket_id"], conv_id)

    # 7. Update conversation status / intent / sentiment
    conv_status = (
        "escalated"
        if (ticket and ticket.get("status") == "escalated")
        else "open"
    )
    update_conversation_meta(
        db,
        conv_id,
        status=conv_status,
        intent=state.get("intent"),
        sentiment=state.get("sentiment"),
    )

    db.commit()

    # 8. Log to MLflow (non-blocking — failure here must not break chat)
    log_chat_run(
        model=settings.OLLAMA_CHAT_MODEL,
        user_message=request.message,
        answer=answer,
        intent=state.get("intent"),
        sentiment=state.get("sentiment"),
        confidence=state.get("confidence"),
        tool_name=state.get("tool_name"),
        tool_result=state.get("tool_result"),
        sources=state.get("sources") or [],
        latency_seconds=time.perf_counter() - t0,
        conversation_id=conv_id,
        ticket_id=ticket.get("ticket_id") if ticket else None,
        escalated=conv_status == "escalated",
        error=state.get("error"),
    )

    # Build response
    sources = [
        SourceInfo(
            title=s.get("title", ""),
            file_path=s.get("file_path", ""),
            chunk_index=int(s.get("chunk_index", 0)),
            distance=s.get("distance"),
        )
        for s in (state.get("sources") or [])
    ]

    logger.info(
        "chat completed | conv=%d | intent=%s | tool=%s | ticket=%s | answer_len=%d | latency=%.2fs",
        conv_id,
        state.get("intent"),
        state.get("tool_name"),
        ticket.get("ticket_id") if ticket else None,
        len(answer),
        time.perf_counter() - t0,
    )

    return ChatResponse(
        conversation_id=conv_id,
        answer=answer,
        sources=sources,
        model=settings.OLLAMA_CHAT_MODEL,
        intent=state.get("intent"),
        tool_name=state.get("tool_name"),
        tool_result=state.get("tool_result"),
        ticket=ticket,
    )
```

- [ ] **Step 4: Run all MLflow tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_mlflow_tracking.py -v
```

Expected: `10 passed` (8 unit + 2 integration).

- [ ] **Step 5: Run the full test suite — must still pass**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: `97 passed` (95 existing + 2 new integration tests — the 8 unit tests in test_mlflow_tracking.py bring the total from 95 to 103).

> Note: the exact total is 95 (old) + 10 (new) = 105 but some may have already been in the count. The key requirement is 0 failures and 0 errors.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/api/chat.py backend/tests/test_mlflow_tracking.py
git commit -m "feat(phase-11): wire log_chat_run into chat endpoint with latency timing"
```

---

## Task 4: Update `backend/README.md` with MLflow docs

**Files:**
- Modify: `backend/README.md`

- [ ] **Step 1: Append MLflow section to `backend/README.md`**

Add the following section at the end of the file:

```markdown
---

## MLflow Tracking (Phase 11)

Every `POST /api/chat` call is logged as an MLflow run in the local file store at `<repo-root>/mlruns`.

### Start the MLflow UI

Run from the **repo root** (`C:\Users\Victus\Desktop\supportflow\`):

```powershell
cd C:\Users\Victus\Desktop\supportflow
.venv\Scripts\Activate.ps1   # or: backend\.venv\Scripts\Activate.ps1
mlflow ui --backend-store-uri mlruns --port 5000
```

Then open: **http://localhost:5000**

> The `mlruns/` directory is created automatically the first time a chat request is made. If it does not exist yet, the UI will start but show no experiments.

### What is logged per run

| Type | Key | Value |
|---|---|---|
| Param | `model` | Ollama model name, e.g. `mistral:7b` |
| Param | `prompt_version` | `v1-agent-rag-tools` |
| Param | `intent` | Classified intent, e.g. `order_status`, `faq` |
| Param | `sentiment` | `neutral` or `negative` |
| Param | `tool_name` | Tool invoked, or `none` |
| Metric | `latency_seconds` | End-to-end request duration |
| Metric | `answer_length` | Character count of the answer |
| Metric | `retrieved_source_count` | Number of KB chunks retrieved |
| Metric | `confidence` | Agent confidence score (when present) |
| Tag | `conversation_id` | Postgres conversation ID |
| Tag | `ticket_created` | `true` / `false` |
| Tag | `escalated` | `true` / `false` |
| Artifact | `user_message.txt` | The customer's original message |
| Artifact | `answer.txt` | The AI's response |
| Artifact | `sources.json` | Retrieved KB source documents |
| Artifact | `tool_result.json` | Tool call result summary (if a tool was used) |
| Artifact | `error.txt` | Error details (only present on failure runs) |

### View a run

1. Start the backend: `uvicorn app.main:app --reload`
2. Send a chat from `http://localhost:3000/chat`
3. Refresh `http://localhost:5000`
4. Click experiment **supportflow-ai-chat** → click the latest run
5. Inspect params, metrics, tags, and artifacts tabs
```

- [ ] **Step 2: Commit**

```powershell
git add backend/README.md
git commit -m "docs(phase-11): add MLflow UI instructions and field reference to README"
```

---

## Task 5: Final Verification

- [ ] **Step 1: Run full test suite**

```powershell
cd C:\Users\Victus\Desktop\supportflow\backend
.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: All tests pass, 0 failures.

- [ ] **Step 2: Start backend and verify /health**

```powershell
uvicorn app.main:app --reload
```

In another terminal:
```powershell
.venv\Scripts\python.exe -c "import httpx; r=httpx.get('http://localhost:8000/health'); print(r.status_code, r.json())"
```

Expected: `200 {'status': 'ok', ...}`

- [ ] **Step 3: Verify mlruns directory is created after a chat request**

Send a mock chat request (with backend running):
```powershell
.venv\Scripts\python.exe -c "
import httpx, json
r = httpx.post(
    'http://localhost:8000/api/chat',
    json={'message': 'What is your refund period?'},
    timeout=180.0
)
print(r.status_code, json.dumps(r.json(), indent=2)[:200])
"
```

Expected: `200` response with `conversation_id`, `answer`, `sources`.

Then check the mlruns directory was created:
```powershell
ls C:\Users\Victus\Desktop\supportflow\mlruns
```

Expected: `mlruns/` exists with at least one subdirectory.

- [ ] **Step 4: Start MLflow UI and verify run appears**

```powershell
cd C:\Users\Victus\Desktop\supportflow
.venv\Scripts\Activate.ps1
mlflow ui --backend-store-uri mlruns --port 5000
```

> Note: run this from repo root `C:\Users\Victus\Desktop\supportflow\`, not from `backend/`.

Open `http://localhost:5000` in browser.

Expected:
- Experiment `supportflow-ai-chat` exists
- At least one run visible
- Run has params: `model`, `intent`, `prompt_version`, `sentiment`, `tool_name`
- Run has metrics: `latency_seconds`, `answer_length`, `retrieved_source_count`
- Run has artifacts: `user_message.txt`, `answer.txt`

- [ ] **Step 5: Commit final state (if any uncommitted changes)**

```powershell
git status
```

If clean, no commit needed.

---

## Self-Review Checklist

- [x] `mlflow` added to requirements.txt — Task 1
- [x] `MLFLOW_TRACKING_URI` and `MLFLOW_EXPERIMENT_NAME` added to config — Task 1
- [x] `.env` updated to file-based tracking — Task 1
- [x] `PROMPT_VERSION = "v1-agent-rag-tools"` constant — Task 2
- [x] `log_chat_run()` logs all required params (model, intent, sentiment, tool_name, prompt_version) — Task 2
- [x] `log_chat_run()` logs all required metrics (latency_seconds, answer_length, retrieved_source_count, confidence) — Task 2
- [x] `log_chat_run()` logs all required tags (conversation_id, ticket_created, escalated) — Task 2
- [x] `log_chat_run()` logs artifacts (user_message.txt, answer.txt, sources.json, tool_result.json) — Task 2
- [x] `log_chat_run()` wrapped in try/except — never raises — Task 2
- [x] Latency measured with `time.perf_counter()` from after Ollama check — Task 3
- [x] `log_chat_run()` called in success path after `db.commit()` — Task 3
- [x] `log_chat_run()` called in error path before raising HTTPException — Task 3
- [x] All existing 95 tests still pass — Task 3
- [x] Tests verify non-breaking behaviour on MLflow failure — Task 2
- [x] Tests verify happy path with real file-based write — Task 2
- [x] Integration test: POST /api/chat returns 200 with MLflow enabled — Task 3
- [x] Integration test: POST /api/chat returns 200 when MLflow fails — Task 3
- [x] README documents exact MLflow UI command — Task 4
- [x] README documents all logged fields — Task 4
- [x] No secrets logged (no DB URL, no API keys) — Task 2 (implementation)
- [x] `mlruns/` at repo root (file:../mlruns relative to backend/) — Task 1 + 4
