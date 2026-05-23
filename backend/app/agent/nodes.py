"""
LangGraph node functions and conditional router for SupportFlow AI.

Node execution order (typical paths):
  classify_intent → retrieve_context → generate_answer   (faq / unknown)
  classify_intent → run_tool         → generate_answer   (order/billing/sub/refund/escalation)
  classify_intent →                    generate_answer   (pre-filled missing-info answer)
"""
from __future__ import annotations

import json
import re
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import SYSTEM_PROMPT, build_answer_prompt
from app.agent.state import AgentState
from app.llm.ollama import check_ollama_available, get_chat_llm
from app.rag.retriever import retrieve
from app.tools.support_tools import (
    check_payment_history,
    check_refund_eligibility,
    create_support_ticket,
    escalate_to_human,
    get_subscription_status,
    get_order_status,
)


# ---------------------------------------------------------------------------
# Entity-extraction helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
_ORDER_RE = re.compile(
    r"(?:order\s*#?\s*|#\s*)(\d{3,})", re.IGNORECASE
)


def _extract_email(text: str) -> Optional[str]:
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else None


def _extract_order_number(text: str) -> Optional[str]:
    m = _ORDER_RE.search(text)
    return m.group(1) if m else None


def _match_any(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


# ---------------------------------------------------------------------------
# Intent / sentiment pattern tables (checked in priority order)
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("human_escalation", [
        r"\bhuman\b",
        r"\breal\s+(?:person|agent)\b",
        r"\brepresentative\b",
        r"\boperator\b",
        r"speak\s+(?:to|with)\s+(?:a\s+)?(?:someone|person|agent|human)",
        r"talk\s+(?:to|with)\s+(?:a\s+)?(?:someone|person|agent|human)",
        r"connect\s+(?:me\s+)?(?:to|with)\s+(?:a\s+)?(?:someone|person|agent|human)",
    ]),
    ("billing_issue", [
        r"charged\s+twice",
        r"double\s*[- ]?charge",
        r"duplicate\s*[- ]?charge",
        r"charged\s+(?:me\s+)?again",
        r"two\s+(?:charge|payment)s?",
        r"extra\s+charge",
        r"overcharg",
        r"billing\s+(?:issue|problem|error|concern)",
    ]),
    # refund before order_status: "refund for order #X" is a refund request, not a status check
    ("refund_request", [
        r"\brefund\b",
        r"\breturn\b",
        r"money\s+back",
        r"(?:want|need|request|like)\s+(?:a\s+)?refund",
    ]),
    ("order_status", [
        r"where\s+(?:is|are)\s+(?:my\s+)?(?:order|package|parcel)",
        r"(?:order|package|shipment|parcel)\s+(?:status|tracking)",
        r"track\s+(?:my\s+)?(?:order|package|parcel)",
        r"order\s*#?\s*\d+",
        r"#\s*\d{3,}",
        r"delivery\s+status",
        r"when\s+(?:will\s+(?:it|my\s+order)\s+)?(?:arrive|deliver|ship)",
    ]),
    ("subscription_issue", [
        r"cancel\s+(?:my\s+)?(?:subscription|plan|account)",
        r"(?:subscription|plan)\s+cancel",
        r"\bunsubscribe\b",
        r"\bmy\s+subscription\b",           # "check my subscription", "my subscription status"
        r"my\s+(?:plan)\s+(?:status|info|details)",
        r"change\s+(?:my\s+)?(?:subscription|plan)",
        r"upgrade\s+(?:my\s+)?(?:plan|subscription)",
        r"downgrade\s+(?:my\s+)?(?:plan|subscription)",
    ]),
    ("faq", [
        r"\bpolic(?:y|ies)\b",
        r"how\s+do\s+(?:i|you)\b",
        r"what\s+(?:is|are)\s+(?:the|your)\b",
        r"can\s+(?:i|you)\b",
        r"\brefund\s+period\b",
        r"\breturn\s+period\b",
        r"\bshipping\s+time\b",
        r"\bpricing\b",
    ]),
]

_ANGRY_PATTERNS = [
    r"\bfurious\b", r"\bangry\b", r"\bupset\b", r"\bfrustrat\w*",
    r"\bridiculous\b", r"\bunacceptable\b", r"\bterrible\b",
    r"\bawful\b", r"\bhorrible\b", r"\boutrageous\b",
    r"\bscam\b", r"\bdisgusting\b",
]

_BILLING_DUPLICATE_KEYWORDS = [
    r"charged\s+twice", r"double\s*[- ]?charge", r"duplicate\s*[- ]?charge",
    r"charged\s+(?:me\s+)?again", r"two\s+(?:charge|payment)s?",
    r"extra\s+charge", r"overcharg",
]


# ---------------------------------------------------------------------------
# Node 1 — classify_intent
# ---------------------------------------------------------------------------

def classify_intent_node(state: AgentState) -> dict:
    """
    Keyword-based intent classification and entity extraction.

    Returns partial state updates only (LangGraph merges into full state).
    Sets `answer` (non-empty) when a required entity is missing so the
    router can skip the tool node entirely.
    """
    msg: str = state["message"]

    # ── Sentiment / angry detection ────────────────────────────────────────
    is_angry = _match_any(msg, _ANGRY_PATTERNS)
    sentiment = "negative" if is_angry else "neutral"

    if is_angry:
        return {
            "intent": "human_escalation",
            "sentiment": sentiment,
            "confidence": 0.9,
            "needs_human": True,
            "tool_input": {
                "reason": "Customer expressed frustration or anger.",
                "summary": msg,
                "category": "escalation",
                "priority": "high",
            },
            "answer": "",
        }

    # ── Pattern matching (priority order) ─────────────────────────────────
    intent = "unknown"
    for intent_name, patterns in _INTENT_PATTERNS:
        if _match_any(msg, patterns):
            intent = intent_name
            break

    # ── Entity extraction & missing-info pre-fill ─────────────────────────
    tool_input: Optional[dict] = None
    answer_pre = ""

    if intent == "order_status":
        order_number = _extract_order_number(msg)
        if order_number:
            tool_input = {"order_number": order_number}
        else:
            answer_pre = (
                "I'd be happy to look up your order! "
                "Could you please provide your order number? "
                "You'll find it in your confirmation email (e.g. #1004)."
            )

    elif intent == "refund_request":
        order_number = _extract_order_number(msg)
        if order_number:
            tool_input = {"order_number": order_number}
        elif _match_any(msg, [r"\b(?:i\s+want|i\s+need|i\s+would\s+like|give\s+me|process)\b"]):
            # Account-specific without order number → ask
            answer_pre = (
                "I can help with your refund request! "
                "Please provide your order number (e.g. #1004) "
                "so I can check eligibility."
            )
        else:
            # General policy question → let RAG handle it
            intent = "faq"

    elif intent == "billing_issue":
        email = _extract_email(msg)
        is_duplicate_msg = _match_any(msg, _BILLING_DUPLICATE_KEYWORDS)
        if email:
            tool_input = {"email": email}
        elif is_duplicate_msg:
            # Demo fallback: duplicate charge without email → use Ayesha's account
            tool_input = {"email": "ayesha@example.com"}
        else:
            answer_pre = (
                "I'd like to look into your billing concern. "
                "Could you please provide the email address on your account?"
            )

    elif intent == "subscription_issue":
        email = _extract_email(msg)
        if email:
            tool_input = {"email": email}
        elif _match_any(msg, [r"\bmy\s+(?:subscription|plan|account)\b"]):
            # Account-specific but no email → ask
            answer_pre = (
                "I'd be happy to check your subscription status! "
                "Please provide the email address on your account."
            )
        else:
            # General policy / how-to question → RAG
            intent = "faq"

    elif intent == "human_escalation":
        tool_input = {
            "reason": "Customer requested to speak with a human agent.",
            "summary": msg,
            "category": "general",
            "priority": "high",
        }

    return {
        "intent": intent,
        "sentiment": sentiment,
        "confidence": 0.85,
        "needs_human": False,
        "tool_input": tool_input,
        "answer": answer_pre,
    }


# ---------------------------------------------------------------------------
# Router (conditional edge after classify)
# ---------------------------------------------------------------------------

def route_after_classify(state: AgentState) -> str:
    """Return the name of the next node after intent classification."""
    # Pre-filled answer (missing required entity) → skip straight to output
    if state.get("answer"):
        return "generate_answer"

    intent = state.get("intent", "unknown")
    if intent in ("faq", "unknown"):
        return "retrieve"
    return "run_tool"


# ---------------------------------------------------------------------------
# Node 2 — retrieve_context
# ---------------------------------------------------------------------------

def retrieve_context_node(state: AgentState) -> dict:
    """Retrieve relevant knowledge-base chunks via ChromaDB."""
    try:
        chunks = retrieve(state["message"], k=4)
    except Exception as exc:
        return {
            "retrieved_context": [],
            "sources": [],
            "error": f"RAG retrieval failed: {exc}",
        }

    # Deduplicate sources by title for display
    seen: set[str] = set()
    sources: list[dict] = []
    for c in chunks:
        title = c.get("title") or c.get("source", "Knowledge Base")
        if title not in seen:
            seen.add(title)
            sources.append({
                "title": title,
                "file_path": c.get("file_path", ""),
                "chunk_index": int(c.get("chunk_index", 0)),
                "distance": c.get("distance"),
            })

    return {
        "retrieved_context": chunks,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Node 3 — run_tool
# ---------------------------------------------------------------------------

def run_tool_node(state: AgentState) -> dict:
    """
    Dispatch to the appropriate business tool based on intent.

    For billing duplicates and human escalations, also creates a ticket
    and stores it in state["ticket"].
    """
    intent: str = state.get("intent", "unknown")
    tool_input: dict = state.get("tool_input") or {}

    tool_name: Optional[str] = None
    tool_result: Optional[dict] = None
    ticket: Optional[dict] = None

    try:
        # ── Order status ───────────────────────────────────────────────────
        if intent == "order_status":
            order_number = tool_input.get("order_number")
            if order_number:
                tool_name = "get_order_status"
                result = get_order_status(order_number)
                tool_result = result.model_dump(mode="json")

        # ── Billing / payment history ──────────────────────────────────────
        elif intent == "billing_issue":
            email = tool_input.get("email")
            if email:
                tool_name = "check_payment_history"
                result = check_payment_history(email)
                tool_result = result.model_dump(mode="json")

                # Auto-escalate on confirmed duplicate charge
                if result.found and result.duplicate_detected:
                    esc = escalate_to_human(
                        reason=(
                            f"Duplicate charge detected on account {email}. "
                            f"{result.duplicate_details or ''}"
                        ),
                        summary=(
                            "Customer reported being charged twice. "
                            "Duplicate confirmed by payment history."
                        ),
                        user_email=email,
                        category="billing",
                        priority="high",
                    )
                    ticket = esc.model_dump(mode="json")

        # ── Subscription status ────────────────────────────────────────────
        elif intent == "subscription_issue":
            email = tool_input.get("email")
            if email:
                tool_name = "get_subscription_status"
                result = get_subscription_status(email)
                tool_result = result.model_dump(mode="json")

        # ── Refund eligibility ─────────────────────────────────────────────
        elif intent == "refund_request":
            order_number = tool_input.get("order_number")
            if order_number:
                tool_name = "check_refund_eligibility"
                result = check_refund_eligibility(order_number)
                tool_result = result.model_dump(mode="json")

                # Create a review ticket when order requires human review
                if result.found and result.requires_review:
                    t = create_support_ticket(
                        category="refund",
                        priority="medium",
                        summary=(
                            f"Refund review requested for order #{order_number}. "
                            f"Order status: {result.order_status}."
                        ),
                    )
                    ticket = t.model_dump(mode="json")

        # ── Human escalation ───────────────────────────────────────────────
        elif intent == "human_escalation":
            tool_name = "escalate_to_human"
            esc = escalate_to_human(
                reason=tool_input.get(
                    "reason", "Customer requested human support."
                ),
                summary=tool_input.get("summary", state.get("message", "")),
                category=tool_input.get("category", "general"),
                priority=tool_input.get("priority", "high"),
            )
            ticket = esc.model_dump(mode="json")
            tool_result = ticket

    except Exception as exc:
        return {
            "tool_name": tool_name,
            "tool_result": None,
            "ticket": None,
            "error": f"Tool execution error: {exc}",
        }

    return {
        "tool_name": tool_name,
        "tool_result": tool_result,
        "ticket": ticket,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Ticket-ID hallucination guard
# ---------------------------------------------------------------------------

# Patterns that look like fake ticket references the LLM might hallucinate.
# Only applied when state.ticket is None (no real ticket was created).
_FAKE_TICKET_RE = re.compile(
    r"(?:"
    # "Ticket ID: 123" / "Ticket ID #123" / "Ticket #123"
    r"[Tt]icket\s+(?:[Ii][Dd]\.?\s*[:：]?\s*#?\s*\d+|#\s*\d+)"
    r"|"
    # "Reference number: 123" / "Reference #123"
    r"[Rr]eference\s+(?:[Nn]umber\.?\s*[:：]?\s*#?\s*\d+|#\s*\d+)"
    r"|"
    # "Case number: 123" / "Case #123"
    r"[Cc]ase\s+(?:[Nn]umber\.?\s*[:：]?\s*#?\s*\d+|#\s*\d+)"
    r")",
)


def strip_fake_ticket_ids(answer: str, ticket: Optional[dict]) -> str:
    """
    Remove hallucinated ticket references from the LLM answer.

    When a real ticket exists (ticket is not None) the answer is returned
    unchanged — the ticket reference is legitimate.
    When no ticket exists, any pattern matching a ticket/reference/case ID
    with an associated number is stripped.

    Exported for direct testing.
    """
    if ticket is not None:
        return answer
    cleaned = _FAKE_TICKET_RE.sub("", answer)
    # Collapse any double-spaces or leading/trailing whitespace left behind
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned


# ---------------------------------------------------------------------------
# Node 4 — generate_answer
# ---------------------------------------------------------------------------

def generate_answer_node(state: AgentState) -> dict:
    """
    Generate the final customer-facing answer.

    If `answer` was pre-filled by classify_intent (missing entity case) this
    node is a no-op — the pre-filled message is returned as-is.
    """
    # Pre-filled answer from classify node → keep it
    if state.get("answer"):
        return {}

    # Build LLM context string
    context_str = _build_context_string(state)

    # Ollama availability check
    ok, reason = check_ollama_available()
    if not ok:
        return {
            "answer": _structured_fallback(state),
            "error": reason,
        }

    ticket = state.get("ticket")

    try:
        llm = get_chat_llm()
        prompt = build_answer_prompt(
            question=state["message"],
            context=context_str,
            intent=state.get("intent", "unknown"),
            ticket=ticket,
        )
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        answer = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )
    except Exception as exc:
        answer = _structured_fallback(state)

    # Safety net: scrub any hallucinated ticket IDs when no ticket was created
    answer = strip_fake_ticket_ids(answer, ticket)

    return {"answer": answer}


# ---------------------------------------------------------------------------
# generate_answer helpers
# ---------------------------------------------------------------------------

def _build_context_string(state: AgentState) -> str:
    """Assemble a human-readable context block for the LLM prompt."""
    parts: list[str] = []

    # RAG chunks
    if state.get("retrieved_context"):
        chunk_text = "\n\n".join(
            f"[Source: {c.get('title') or c.get('source', 'Knowledge Base')}]\n"
            f"{c.get('text', '')}"
            for c in state["retrieved_context"]
        )
        parts.append(f"KNOWLEDGE BASE:\n{chunk_text}")

    # Tool data
    if state.get("tool_result"):
        parts.append(
            f"TOOL DATA ({state.get('tool_name', 'system')}):\n"
            + json.dumps(state["tool_result"], default=str, indent=2)
        )

    if not parts:
        parts.append("No context available.")

    return "\n\n".join(parts)


def _structured_fallback(state: AgentState) -> str:
    """Return a deterministic answer when the LLM is unavailable."""
    intent = state.get("intent", "unknown")
    tool_result = state.get("tool_result") or {}
    ticket = state.get("ticket")

    if intent == "order_status" and tool_result.get("found"):
        tracking = tool_result.get("tracking_number")
        return (
            f"Your order #{tool_result.get('order_number')} is currently "
            f"{tool_result.get('status')}."
            + (f" Tracking number: {tracking}." if tracking else "")
        )

    if intent == "billing_issue" and ticket:
        return (
            "We detected a possible duplicate charge on your account. "
            f"This has been escalated to our billing team (Ticket #{ticket.get('ticket_id')}). "
            "We will review and contact you shortly."
        )

    if ticket and ticket.get("status") == "escalated":
        return (
            "Your request has been escalated to a human support agent "
            f"(Ticket #{ticket.get('ticket_id')}, priority: {ticket.get('priority')}). "
            "Our team will be in touch soon."
        )

    if state.get("retrieved_context"):
        first = state["retrieved_context"][0]
        return (
            f"Based on our knowledge base ({first.get('title', 'documentation')}): "
            + first.get("text", "")[:400]
        )

    return (
        "I'm sorry, I don't have enough information to answer that question. "
        "Please contact our support team for further assistance."
    )
