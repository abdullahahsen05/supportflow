"""
Tests for Phase 7 LangGraph agent workflow.

Two layers:
  1. Intent classification (pure Python, no I/O) — always run
  2. Tool dispatch (needs DB / Postgres) — integration tests

Full LLM pipeline (Ollama + mistral:7b) is exercised by the verify script
to avoid non-deterministic assertions in the test suite.

Run from backend/ with .venv active:
    pytest tests/test_agent_workflow.py -v
"""
from __future__ import annotations

import pytest

from app.agent.nodes import classify_intent_node, run_tool_node


# ===========================================================================
# Helper: minimal state dict for testing classify in isolation
# ===========================================================================

def _msg_state(message: str) -> dict:
    """Minimal state dict satisfying classify_intent_node's read of state['message']."""
    return {"message": message}


def _full_state(message: str, intent: str, tool_input: dict | None = None) -> dict:
    """Full state dict for run_tool_node tests."""
    return {
        "message": message,
        "intent": intent,
        "sentiment": "neutral",
        "confidence": 0.85,
        "needs_human": False,
        "retrieved_context": [],
        "sources": [],
        "tool_name": None,
        "tool_input": tool_input,
        "tool_result": None,
        "ticket": None,
        "answer": "",
        "error": None,
    }


# ===========================================================================
# 1. Intent classification — pure Python, no I/O
# ===========================================================================

class TestClassifyIntent:

    def test_faq_refund_period(self):
        result = classify_intent_node(_msg_state("What is your refund period?"))
        # Spec: faq or refund_request both acceptable as long as RAG is used.
        # Without an order number, refund_request redirects to faq internally.
        assert result["intent"] in ("faq", "refund_request")
        # tool_input should be None (no order number extracted)
        assert result.get("tool_input") is None

    def test_order_status_with_number(self):
        result = classify_intent_node(_msg_state("Where is my order #1004?"))
        assert result["intent"] == "order_status"
        assert result["tool_input"] is not None
        assert result["tool_input"]["order_number"] == "1004"

    def test_order_status_without_number(self):
        result = classify_intent_node(_msg_state("Where is my order?"))
        assert result["intent"] == "order_status"
        # No order number → pre-filled answer asking for one
        assert result.get("answer")
        assert result.get("tool_input") is None

    def test_billing_duplicate_charge(self):
        result = classify_intent_node(_msg_state("I was charged twice this month."))
        assert result["intent"] == "billing_issue"
        # Demo fallback email should be set
        assert result["tool_input"] is not None
        assert result["tool_input"].get("email") is not None

    def test_human_escalation_explicit(self):
        result = classify_intent_node(_msg_state("I want to speak to a human."))
        assert result["intent"] == "human_escalation"
        assert result["tool_input"] is not None

    def test_human_escalation_angry_sentiment(self):
        result = classify_intent_node(_msg_state("This is absolutely ridiculous and outrageous!"))
        assert result["intent"] == "human_escalation"
        assert result["sentiment"] == "negative"
        assert result["needs_human"] is True

    def test_unknown_alien_question(self):
        # "policy" keyword may route to faq; both faq and unknown are acceptable
        # as long as the RAG path finds no relevant content and the LLM does not
        # invent a policy (verified by the verify script, not asserted on wording here).
        result = classify_intent_node(
            _msg_state("What is CloudDesk's policy on alien spaceship rentals?")
        )
        assert result["intent"] in ("faq", "unknown")

    def test_subscription_with_email(self):
        result = classify_intent_node(
            _msg_state("Can you check my subscription for ayesha@example.com?")
        )
        assert result["intent"] == "subscription_issue"
        assert result["tool_input"]["email"] == "ayesha@example.com"

    def test_refund_with_order_number(self):
        result = classify_intent_node(_msg_state("I want a refund for order #1005"))
        assert result["intent"] == "refund_request"
        assert result["tool_input"]["order_number"] == "1005"

    def test_missing_order_number_pre_fills_answer(self):
        """Missing order number must pre-fill answer, not leave it empty."""
        result = classify_intent_node(_msg_state("Where is my order?"))
        assert bool(result.get("answer")), "Expected pre-filled answer for missing order number"


# ===========================================================================
# 2. Tool dispatch — integration tests (needs Postgres on port 5433)
# ===========================================================================

class TestToolDispatch:

    def test_order_status_found(self):
        """get_order_status('1004') returns shipped + TRK-CD-1004."""
        state = _full_state(
            "Where is my order #1004?",
            intent="order_status",
            tool_input={"order_number": "1004"},
        )
        result = run_tool_node(state)
        assert result["tool_name"] == "get_order_status"
        assert result["tool_result"] is not None
        assert result["tool_result"]["found"] is True
        assert result["tool_result"]["status"] == "shipped"
        assert result["tool_result"]["tracking_number"] == "TRK-CD-1004"
        assert result["ticket"] is None  # no ticket for normal order lookup

    def test_order_status_not_found(self):
        state = _full_state(
            "Where is order #9999?",
            intent="order_status",
            tool_input={"order_number": "9999"},
        )
        result = run_tool_node(state)
        assert result["tool_result"]["found"] is False

    def test_billing_duplicate_detected_and_escalated(self):
        """Duplicate payment for ayesha → duplicate_detected + escalated ticket."""
        state = _full_state(
            "I was charged twice this month.",
            intent="billing_issue",
            tool_input={"email": "ayesha@example.com"},
        )
        result = run_tool_node(state)
        assert result["tool_name"] == "check_payment_history"
        assert result["tool_result"]["found"] is True
        assert result["tool_result"]["duplicate_detected"] is True
        # Auto-escalation ticket must be created
        assert result["ticket"] is not None
        assert result["ticket"]["status"] == "escalated"
        assert result["ticket"]["priority"] == "high"

    def test_billing_no_duplicate(self):
        state = _full_state(
            "billing question",
            intent="billing_issue",
            tool_input={"email": "omar@example.com"},
        )
        result = run_tool_node(state)
        assert result["tool_result"]["duplicate_detected"] is False
        assert result["ticket"] is None  # no escalation when no duplicate

    def test_human_escalation_creates_ticket(self):
        """escalate_to_human → ticket with status=escalated, priority=high."""
        state = _full_state(
            "I want to speak to a human.",
            intent="human_escalation",
            tool_input={
                "reason": "Customer requested human support.",
                "summary": "I want to speak to a human.",
                "category": "general",
                "priority": "high",
            },
        )
        result = run_tool_node(state)
        assert result["tool_name"] == "escalate_to_human"
        assert result["ticket"] is not None
        assert result["ticket"]["status"] == "escalated"
        assert result["ticket"]["priority"] == "high"
        assert result["ticket"]["ticket_id"] > 0

    def test_refund_eligibility_shipped_creates_review_ticket(self):
        """Order #1004 is shipped → requires_review → ticket created."""
        state = _full_state(
            "I want a refund for order #1004",
            intent="refund_request",
            tool_input={"order_number": "1004"},
        )
        result = run_tool_node(state)
        assert result["tool_name"] == "check_refund_eligibility"
        assert result["tool_result"]["found"] is True
        assert result["tool_result"]["requires_review"] is True
        assert result["ticket"] is not None  # review ticket created

    def test_refund_eligibility_delivered_no_ticket(self):
        """Order #1005 delivered → eligible, no review ticket needed."""
        state = _full_state(
            "I want a refund for order #1005",
            intent="refund_request",
            tool_input={"order_number": "1005"},
        )
        result = run_tool_node(state)
        assert result["tool_result"]["eligible"] is True
        assert result["ticket"] is None  # no review ticket for eligible order

    def test_subscription_ayesha_pro_active(self):
        state = _full_state(
            "subscription status for ayesha@example.com",
            intent="subscription_issue",
            tool_input={"email": "ayesha@example.com"},
        )
        result = run_tool_node(state)
        assert result["tool_name"] == "get_subscription_status"
        assert result["tool_result"]["found"] is True
        assert result["tool_result"]["plan_name"] == "Pro"
        assert result["tool_result"]["status"] == "active"


# ===========================================================================
# 3. Ticket-ID hallucination guard — pure Python, no I/O
# ===========================================================================

from app.agent.nodes import strip_fake_ticket_ids
from app.agent.prompts import build_answer_prompt


class TestTicketHallucinationGuard:
    """
    Tests for the two-layer hallucination defence:
      1. build_answer_prompt() injects an explicit no-ticket / real-ticket block
      2. strip_fake_ticket_ids() scrubs residual fake IDs from LLM output
    """

    # ── strip_fake_ticket_ids ─────────────────────────────────────────────

    def test_strips_ticket_id_colon_format(self):
        dirty = "Your order is shipped. Ticket ID: 1234567890"
        assert "1234567890" not in strip_fake_ticket_ids(dirty, ticket=None)

    def test_strips_ticket_hash_format(self):
        dirty = "Here you go. ticket #9999 has been logged."
        assert "9999" not in strip_fake_ticket_ids(dirty, ticket=None)

    def test_strips_ticket_id_hash_format(self):
        dirty = "Reference is Ticket ID #777."
        assert "777" not in strip_fake_ticket_ids(dirty, ticket=None)

    def test_strips_reference_number(self):
        dirty = "Your reference number: 42 has been noted."
        # "reference number: 42" should be scrubbed
        assert "reference number" not in strip_fake_ticket_ids(dirty, ticket=None).lower()

    def test_preserves_real_ticket_when_ticket_exists(self):
        dirty = "Your Ticket #42 has been created."
        real_ticket = {"ticket_id": 42, "status": "escalated", "priority": "high"}
        result = strip_fake_ticket_ids(dirty, ticket=real_ticket)
        assert "42" in result, "Real ticket ID must not be stripped"

    def test_no_change_when_no_fake_ids(self):
        clean = "Your order has been shipped and is on its way."
        assert strip_fake_ticket_ids(clean, ticket=None) == clean

    def test_no_change_for_plain_numbers(self):
        """Numbers not preceded by ticket/reference keywords must be preserved."""
        clean = "Your order #1004 is shipped with tracking TRK-CD-1004."
        result = strip_fake_ticket_ids(clean, ticket=None)
        assert "1004" in result

    def test_strips_multiple_fake_ids(self):
        dirty = "Ticket ID: 111 and also ticket #222 were created."
        result = strip_fake_ticket_ids(dirty, ticket=None)
        assert "111" not in result
        assert "222" not in result

    # ── build_answer_prompt ───────────────────────────────────────────────

    def test_no_ticket_prompt_contains_critical_rule(self):
        prompt = build_answer_prompt("question?", "context", "faq", ticket=None)
        assert "NO support ticket" in prompt or "NO ticket" in prompt or "no ticket" in prompt.lower()
        assert "CRITICAL" in prompt or "Do NOT" in prompt

    def test_no_ticket_prompt_forbids_ticket_id_phrase(self):
        prompt = build_answer_prompt("question?", "context", "unknown", ticket=None)
        # The prompt must explicitly forbid "Ticket ID:" pattern
        assert "Ticket ID" in prompt or "ticket number" in prompt.lower()

    def test_real_ticket_prompt_contains_exact_id(self):
        t = {"ticket_id": 99, "status": "escalated", "priority": "high"}
        prompt = build_answer_prompt("help!", "context", "human_escalation", ticket=t)
        assert "#99" in prompt or "99" in prompt
        assert "MUST" in prompt or "must" in prompt.lower()

    def test_real_ticket_prompt_contains_status(self):
        t = {"ticket_id": 55, "status": "escalated", "priority": "high"}
        prompt = build_answer_prompt("help!", "context", "human_escalation", ticket=t)
        assert "escalated" in prompt

    def test_no_ticket_and_real_ticket_prompts_differ(self):
        no_ticket = build_answer_prompt("q", "ctx", "faq", ticket=None)
        with_ticket = build_answer_prompt(
            "q", "ctx", "human_escalation",
            ticket={"ticket_id": 7, "status": "escalated", "priority": "high"}
        )
        assert no_ticket != with_ticket
