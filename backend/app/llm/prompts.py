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
