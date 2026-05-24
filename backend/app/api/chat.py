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
    latency_seconds = time.perf_counter() - t0
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
        latency_seconds=latency_seconds,
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
        latency_seconds,
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
