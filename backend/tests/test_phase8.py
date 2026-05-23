"""
Phase 8 tests — conversation persistence + core API endpoints.

Strategy
--------
* POST /api/chat tests mock both check_ollama_available and run_agent so the
  suite runs without Ollama.  A realistic AgentState dict is returned by the
  mock so every persistence path is exercised.
* GET / PATCH / POST endpoints hit the real Postgres (seed data assumed).

Run from backend/ with .venv active:
    pytest tests/test_phase8.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def db() -> Session:
    session = SessionLocal()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Deterministic mock agent states (no Ollama required)
# ---------------------------------------------------------------------------

def _state_faq(message: str = "What is your refund period?") -> dict:
    return {
        "message": message,
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
        "answer": "Our refund period is 30 days from purchase.",
        "error": None,
    }


def _state_order_status() -> dict:
    return {
        "message": "Where is my order #1004?",
        "intent": "order_status",
        "sentiment": "neutral",
        "confidence": 0.85,
        "needs_human": False,
        "retrieved_context": [],
        "sources": [],
        "tool_name": "get_order_status",
        "tool_input": {"order_number": "1004"},
        "tool_result": {
            "found": True,
            "order_number": "1004",
            "status": "shipped",
            "tracking_number": "TRK-CD-1004",
            "customer_name": "Ayesha Khan",
            "customer_email": "ayesha@example.com",
            "total_amount": 149.99,
        },
        "ticket": None,
        "answer": "Your order #1004 is shipped. Tracking: TRK-CD-1004.",
        "error": None,
    }


def _state_billing_escalated() -> dict:
    """Billing duplicate — ticket status is escalated (ticket_id=9001 is fake)."""
    return {
        "message": "I was charged twice this month.",
        "intent": "billing_issue",
        "sentiment": "neutral",
        "confidence": 0.85,
        "needs_human": False,
        "retrieved_context": [],
        "sources": [],
        "tool_name": "check_payment_history",
        "tool_input": {"email": "ayesha@example.com"},
        "tool_result": {
            "found": True,
            "email": "ayesha@example.com",
            "duplicate_detected": True,
            "duplicate_details": "Two payments of $79.99 within 7 days.",
            "payments": [],
        },
        # ticket_id 9001 intentionally non-existent in DB — link_ticket_to_conversation
        # handles missing gracefully (returns without error when ticket not found).
        "ticket": {
            "ticket_id": 9001,
            "status": "escalated",
            "priority": "high",
            "category": "billing",
            "summary": "Duplicate charge escalation",
        },
        "answer": "We detected a duplicate charge and escalated your case.",
        "error": None,
    }


_OLLAMA_CHECK = "app.api.chat.check_ollama_available"
_RUN_AGENT    = "app.api.chat.run_agent"


# ===========================================================================
# 1. POST /api/chat — conversation creation & reuse
# ===========================================================================

class TestChatConversationCreation:

    def test_creates_new_conversation_returns_id(self, client: TestClient):
        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq()):
            resp = client.post("/api/chat", json={"message": "What is your refund period?"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("conversation_id"), int)
        assert data["conversation_id"] > 0

    def test_appends_to_existing_conversation(self, client: TestClient):
        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq("What is your refund period?")):
            resp1 = client.post("/api/chat", json={"message": "What is your refund period?"})
        conv_id = resp1.json()["conversation_id"]

        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq("What is your return period?")):
            resp2 = client.post("/api/chat", json={
                "message": "What is your return period?",
                "conversation_id": conv_id,
            })
        assert resp2.status_code == 200
        assert resp2.json()["conversation_id"] == conv_id

    def test_links_user_by_email(self, client: TestClient, db: Session):
        from app.models.conversation import Conversation
        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq()):
            resp = client.post("/api/chat", json={
                "message": "What is your refund period?",
                "user_email": "ayesha@example.com",
            })
        assert resp.status_code == 200
        conv_id = resp.json()["conversation_id"]

        conv = db.get(Conversation, conv_id)
        db.refresh(conv)
        assert conv.user_id is not None

    def test_response_has_required_fields(self, client: TestClient):
        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq()):
            resp = client.post("/api/chat", json={"message": "Test?"})
        assert resp.status_code == 200
        data = resp.json()
        for field in ("conversation_id", "answer", "sources", "model", "intent"):
            assert field in data


# ===========================================================================
# 2. Message + tool-call persistence
# ===========================================================================

class TestPersistence:

    def test_customer_and_ai_messages_stored(self, client: TestClient, db: Session):
        from app.models.message import Message

        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq("How do I cancel?")):
            resp = client.post("/api/chat", json={"message": "How do I cancel?"})
        conv_id = resp.json()["conversation_id"]

        msgs = (
            db.query(Message)
            .filter(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
            .all()
        )
        senders = [m.sender for m in msgs]
        assert "customer" in senders
        assert "ai" in senders

    def test_order_status_tool_call_persisted(self, client: TestClient, db: Session):
        from app.models.tool_call import ToolCall

        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_order_status()):
            resp = client.post("/api/chat", json={"message": "Where is my order #1004?"})
        conv_id = resp.json()["conversation_id"]

        tc = (
            db.query(ToolCall)
            .filter(ToolCall.conversation_id == conv_id)
            .first()
        )
        assert tc is not None
        assert tc.tool_name == "get_order_status"
        assert tc.success is True

    def test_billing_duplicate_sets_conversation_escalated(
        self, client: TestClient, db: Session
    ):
        from app.models.conversation import Conversation

        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_billing_escalated()):
            resp = client.post("/api/chat", json={
                "message": "I was charged twice this month.",
            })
        assert resp.status_code == 200
        conv_id = resp.json()["conversation_id"]
        assert resp.json()["ticket"]["status"] == "escalated"

        conv = db.get(Conversation, conv_id)
        db.refresh(conv)
        assert conv.status == "escalated"


# ===========================================================================
# 3. GET /api/conversations
# ===========================================================================

class TestConversationsEndpoint:

    def test_list_returns_list(self, client: TestClient):
        resp = client.get("/api/conversations")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_items_have_required_fields(self, client: TestClient):
        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq()):
            client.post("/api/chat", json={"message": "Quick test"})

        resp = client.get("/api/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for field in ("id", "status", "created_at", "updated_at"):
            assert field in data[0]

    def test_detail_returns_messages(self, client: TestClient):
        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq("What is shipping time?")):
            resp = client.post("/api/chat", json={"message": "What is shipping time?"})
        conv_id = resp.json()["conversation_id"]

        detail = client.get(f"/api/conversations/{conv_id}")
        assert detail.status_code == 200
        data = detail.json()
        assert data["id"] == conv_id
        assert len(data["messages"]) >= 2
        senders = {m["sender"] for m in data["messages"]}
        assert "customer" in senders
        assert "ai" in senders

    def test_detail_404_for_missing_conversation(self, client: TestClient):
        resp = client.get("/api/conversations/999999")
        assert resp.status_code == 404


# ===========================================================================
# 4. POST /api/feedback
# ===========================================================================

class TestFeedbackEndpoint:

    def test_stores_feedback(self, client: TestClient):
        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq()):
            chat_resp = client.post("/api/chat", json={"message": "Feedback test"})
        conv_id = chat_resp.json()["conversation_id"]

        resp = client.post("/api/feedback", json={
            "conversation_id": conv_id,
            "feedback_type": "helpful",
            "comment": "Good answer",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["conversation_id"] == conv_id
        assert data["feedback_type"] == "helpful"
        assert data["comment"] == "Good answer"
        assert data["id"] > 0

    def test_feedback_without_comment(self, client: TestClient):
        with patch(_OLLAMA_CHECK, return_value=(True, "")), \
             patch(_RUN_AGENT, return_value=_state_faq()):
            chat_resp = client.post("/api/chat", json={"message": "Quick"})
        conv_id = chat_resp.json()["conversation_id"]

        resp = client.post("/api/feedback", json={
            "conversation_id": conv_id,
            "feedback_type": "not_helpful",
        })
        assert resp.status_code == 201
        assert resp.json()["comment"] is None

    def test_feedback_on_missing_conversation_returns_404(self, client: TestClient):
        resp = client.post("/api/feedback", json={
            "conversation_id": 999999,
            "feedback_type": "helpful",
        })
        assert resp.status_code == 404


# ===========================================================================
# 5. GET /api/tickets
# ===========================================================================

class TestTicketsEndpoint:

    def test_list_returns_list(self, client: TestClient):
        resp = client.get("/api/tickets")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_filter_by_status_escalated(self, client: TestClient):
        resp = client.get("/api/tickets?status=escalated")
        assert resp.status_code == 200
        for ticket in resp.json():
            assert ticket["status"] == "escalated"

    def test_filter_by_priority_high(self, client: TestClient):
        resp = client.get("/api/tickets?priority=high")
        assert resp.status_code == 200
        for ticket in resp.json():
            assert ticket["priority"] == "high"

    def test_ticket_detail(self, client: TestClient, db: Session):
        from app.models.ticket import Ticket as TicketModel
        ticket = db.query(TicketModel).first()
        if ticket is None:
            pytest.skip("No tickets in DB — run seed + agent verify first")

        resp = client.get(f"/api/tickets/{ticket.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == ticket.id
        for field in ("status", "priority", "created_at", "updated_at"):
            assert field in data

    def test_missing_ticket_returns_404(self, client: TestClient):
        resp = client.get("/api/tickets/999999")
        assert resp.status_code == 404


# ===========================================================================
# 6. PATCH /api/tickets/{id}
# ===========================================================================

class TestTicketUpdate:

    def test_updates_status_and_priority(self, client: TestClient):
        from app.tools.support_tools import escalate_to_human
        esc = escalate_to_human(
            reason="Phase 8 PATCH test.",
            summary="PATCH test ticket",
            category="general",
            priority="medium",
        )
        ticket_id = esc.ticket_id

        resp = client.patch(f"/api/tickets/{ticket_id}", json={
            "status": "resolved",
            "priority": "low",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "resolved"
        assert data["priority"] == "low"
        assert data["id"] == ticket_id

    def test_partial_update_leaves_other_fields_unchanged(self, client: TestClient):
        from app.tools.support_tools import escalate_to_human
        esc = escalate_to_human(
            reason="Phase 8 partial update test.",
            summary="Partial update ticket",
            category="general",
            priority="high",
        )
        ticket_id = esc.ticket_id

        resp = client.patch(f"/api/tickets/{ticket_id}", json={"status": "pending"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["priority"] == "high"  # unchanged

    def test_missing_ticket_returns_404(self, client: TestClient):
        resp = client.patch("/api/tickets/999999", json={"status": "closed"})
        assert resp.status_code == 404


# ===========================================================================
# 7. GET /api/knowledge-base
# ===========================================================================

class TestKnowledgeBase:

    def test_returns_8_documents(self, client: TestClient):
        resp = client.get("/api/knowledge-base")
        assert resp.status_code == 200
        assert len(resp.json()) == 8

    def test_all_documents_indexed(self, client: TestClient):
        resp = client.get("/api/knowledge-base")
        for doc in resp.json():
            assert doc["indexed"] is True, f"Doc {doc['id']} not indexed"

    def test_document_fields_present(self, client: TestClient):
        resp = client.get("/api/knowledge-base")
        doc = resp.json()[0]
        for field in ("id", "title", "file_path", "indexed", "created_at"):
            assert field in doc

    def test_reindex_returns_cli_hint(self, client: TestClient):
        resp = client.post("/api/knowledge-base/reindex")
        assert resp.status_code == 200
        data = resp.json()
        assert "cli_command" in data
        assert "app.rag.ingest" in data["cli_command"]
