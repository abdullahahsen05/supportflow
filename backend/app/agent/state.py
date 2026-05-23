"""
LangGraph agent state for SupportFlow AI.

All fields must be present in the initial dict passed to graph.invoke().
Optional fields default to None / empty via run_agent() in graph.py.
"""
from __future__ import annotations

from typing import Optional
from typing import TypedDict


class AgentState(TypedDict):
    # Input
    message: str

    # Classification
    intent: str                     # faq | order_status | refund_request |
                                    # billing_issue | subscription_issue |
                                    # technical_issue | human_escalation | unknown
    sentiment: str                  # neutral | negative
    confidence: float
    needs_human: bool

    # RAG
    retrieved_context: list[dict]   # chunks returned by retriever
    sources: list[dict]             # deduplicated source metadata for response

    # Tool execution
    tool_name: Optional[str]
    tool_input: Optional[dict]      # entities extracted from message
    tool_result: Optional[dict]     # serialised Pydantic result

    # Ticket / escalation
    ticket: Optional[dict]          # created ticket / escalation record

    # Output
    answer: str                     # final customer-facing answer
    error: Optional[str]            # non-fatal error notes
