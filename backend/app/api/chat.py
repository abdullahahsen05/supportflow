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
