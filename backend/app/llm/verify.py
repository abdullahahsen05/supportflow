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

    print("\nCalling LLM (may take 30-60 s on first call)...")
    ai_message = await llm.ainvoke(messages)
    answer = ai_message.content if hasattr(ai_message, "content") else str(ai_message)

    print("\nAnswer:")
    print("-" * 60)
    print(_safe(answer))


if __name__ == "__main__":
    _query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is your refund period?"
    asyncio.run(_run(_query))
