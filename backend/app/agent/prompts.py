"""
Prompt templates for the SupportFlow agent answer-generation node.
"""
from __future__ import annotations

# Ticket instruction removed from the system prompt — it caused the LLM to
# "try to mention a ticket ID" even when none existed.  Ticket rules are
# injected explicitly per-request in build_answer_prompt() below.
SYSTEM_PROMPT = (
    "You are a helpful customer support agent for CloudDesk Inc.\n"
    "Answer the customer's question using ONLY the context and data provided below.\n"
    "Do not invent policies, prices, order details, or facts not present in the context.\n"
    "Be concise, friendly, and professional.\n"
    "If you reference knowledge base information, briefly cite the source document name."
)


def build_answer_prompt(
    question: str,
    context: str,
    intent: str,
    ticket: dict | None = None,
) -> str:
    """
    Return the human-turn prompt fed to the LLM in generate_answer_node.

    The ticket block is always present and is explicit about whether a real
    ticket exists.  This prevents the LLM from hallucinating ticket IDs.
    """
    if ticket:
        real_id = ticket.get("ticket_id")
        ticket_block = (
            "\n\n=== TICKET INFORMATION ===\n"
            f"A real support ticket was created: Ticket #{real_id}.\n"
            f"Status: {ticket.get('status')} | Priority: {ticket.get('priority')}\n"
            f"You MUST reference Ticket #{real_id} in your response.\n"
            "Use ONLY this ticket number. Do NOT use any other number."
        )
    else:
        ticket_block = (
            "\n\n=== TICKET INFORMATION ===\n"
            "NO support ticket was created for this conversation.\n"
            "CRITICAL RULE: Do NOT mention any ticket ID, ticket number, "
            "reference number, or case number whatsoever.\n"
            "Do not use phrases like 'Ticket ID:', 'ticket #', 'reference #', "
            "'case number', or any similar pattern. There is no ticket."
        )

    return (
        f"Context:\n{context}"
        f"{ticket_block}\n\n"
        f"Customer question: {question}\n\n"
        "Answer based only on the above context and ticket information."
    )
