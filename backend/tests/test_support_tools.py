"""
Integration tests for Phase 6 business tools.

Prerequisites:
- Docker Postgres running on port 5433
- python -m app.db.seed already executed (seed data present)

Run from backend/ with .venv active:
    pytest tests/test_support_tools.py -v
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.tools.support_tools import (
    check_payment_history,
    check_refund_eligibility,
    create_support_ticket,
    escalate_to_human,
    get_order_status,
    get_subscription_status,
    get_user_profile,
)


# ---------------------------------------------------------------------------
# Session fixture — shared across all tests in this module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db() -> Session:
    session = SessionLocal()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# get_order_status
# ---------------------------------------------------------------------------

class TestGetOrderStatus:
    def test_order_1004_found(self, db):
        result = get_order_status("1004", db=db)
        assert result.found is True
        assert result.order_number == "1004"
        assert result.status == "shipped"
        assert result.tracking_number == "TRK-CD-1004"
        assert result.total_amount == pytest.approx(149.99, abs=0.01)
        assert result.customer_email == "ayesha@example.com"

    def test_order_9999_not_found(self, db):
        result = get_order_status("9999", db=db)
        assert result.found is False
        assert result.status is None
        assert "9999" in result.message

    def test_order_1005_delivered(self, db):
        result = get_order_status("1005", db=db)
        assert result.found is True
        assert result.status == "delivered"


# ---------------------------------------------------------------------------
# get_user_profile
# ---------------------------------------------------------------------------

class TestGetUserProfile:
    def test_ayesha_found(self, db):
        result = get_user_profile("ayesha@example.com", db=db)
        assert result.found is True
        assert result.email == "ayesha@example.com"
        assert "Ayesha" in result.name
        assert result.role == "customer"
        assert result.id is not None

    def test_unknown_not_found(self, db):
        result = get_user_profile("nobody@nowhere.invalid", db=db)
        assert result.found is False
        assert result.id is None

    def test_admin_user(self, db):
        result = get_user_profile("admin@clouddesk.test", db=db)
        assert result.found is True
        assert result.role == "admin"


# ---------------------------------------------------------------------------
# get_subscription_status
# ---------------------------------------------------------------------------

class TestGetSubscriptionStatus:
    def test_ayesha_pro_active(self, db):
        result = get_subscription_status("ayesha@example.com", db=db)
        assert result.found is True
        assert result.plan_name == "Pro"
        assert result.status == "active"
        assert result.billing_amount == pytest.approx(79.99, abs=0.01)
        assert result.renewal_date is not None

    def test_omar_starter_active(self, db):
        result = get_subscription_status("omar@example.com", db=db)
        assert result.found is True
        assert result.plan_name == "Starter"
        assert result.status == "active"

    def test_sara_pro_past_due(self, db):
        result = get_subscription_status("sara@example.com", db=db)
        assert result.found is True
        assert result.plan_name == "Pro"
        assert result.status == "past_due"

    def test_no_subscription_user(self, db):
        result = get_subscription_status("nobody@nowhere.invalid", db=db)
        assert result.found is False


# ---------------------------------------------------------------------------
# check_payment_history
# ---------------------------------------------------------------------------

class TestCheckPaymentHistory:
    def test_ayesha_duplicate_detected(self, db):
        result = check_payment_history("ayesha@example.com", db=db)
        assert result.found is True
        assert result.duplicate_detected is True
        assert result.duplicate_details is not None
        assert "79.99" in result.duplicate_details
        # Both TXN-AYE-001 and TXN-AYE-002 must appear
        refs = {p.transaction_reference for p in result.payments}
        assert "TXN-AYE-001" in refs
        assert "TXN-AYE-002" in refs

    def test_omar_no_duplicate(self, db):
        result = check_payment_history("omar@example.com", db=db)
        assert result.found is True
        assert result.duplicate_detected is False

    def test_unknown_user(self, db):
        result = check_payment_history("nobody@nowhere.invalid", db=db)
        assert result.found is False

    def test_payments_returned_in_desc_order(self, db):
        result = check_payment_history("ayesha@example.com", db=db)
        dates = [p.payment_date for p in result.payments]
        assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# check_refund_eligibility
# ---------------------------------------------------------------------------

class TestCheckRefundEligibility:
    def test_order_1004_shipped_requires_review(self, db):
        result = check_refund_eligibility("1004", db=db)
        assert result.found is True
        assert result.order_number == "1004"
        assert result.order_status == "shipped"
        assert result.requires_review is True
        # eligible is None (pending review), not False
        assert result.eligible is None

    def test_order_1005_delivered_eligible(self, db):
        result = check_refund_eligibility("1005", db=db)
        assert result.found is True
        assert result.eligible is True
        assert result.requires_review is False

    def test_order_1007_cancelled_not_eligible(self, db):
        result = check_refund_eligibility("1007", db=db)
        assert result.found is True
        assert result.eligible is False

    def test_order_9999_not_found(self, db):
        result = check_refund_eligibility("9999", db=db)
        assert result.found is False


# ---------------------------------------------------------------------------
# create_support_ticket
# ---------------------------------------------------------------------------

class TestCreateSupportTicket:
    def test_creates_ticket_with_user(self, db):
        result = create_support_ticket(
            category="billing",
            priority="medium",
            summary="Test billing inquiry from pytest.",
            user_email="ayesha@example.com",
            db=db,
        )
        assert result.ticket_id > 0
        assert result.status == "open"
        assert result.priority == "medium"
        assert result.category == "billing"
        assert "billing" in result.summary.lower()

    def test_creates_ticket_without_user(self, db):
        result = create_support_ticket(
            category="technical",
            priority="low",
            summary="Anonymous tech question.",
            db=db,
        )
        assert result.ticket_id > 0
        assert result.status == "open"

    def test_ticket_with_escalation_reason_becomes_escalated(self, db):
        result = create_support_ticket(
            category="billing",
            priority="high",
            summary="Escalated via create_support_ticket.",
            escalation_reason="Customer is very upset.",
            db=db,
        )
        assert result.ticket_id > 0
        assert result.status == "escalated"

    def test_ticket_ids_are_unique(self, db):
        r1 = create_support_ticket(
            category="general", priority="low", summary="Ticket A", db=db
        )
        r2 = create_support_ticket(
            category="general", priority="low", summary="Ticket B", db=db
        )
        assert r1.ticket_id != r2.ticket_id


# ---------------------------------------------------------------------------
# escalate_to_human
# ---------------------------------------------------------------------------

class TestEscalateToHuman:
    def test_creates_escalated_ticket(self, db):
        result = escalate_to_human(
            reason="Customer demands human support immediately.",
            summary="Billing dispute unresolved by bot.",
            user_email="ayesha@example.com",
            category="billing",
            priority="high",
            db=db,
        )
        assert result.ticket_id > 0
        assert result.status == "escalated"
        assert result.priority == "high"
        assert "human" in result.reason.lower() or "support" in result.reason.lower()

    def test_escalation_default_priority_is_high(self, db):
        result = escalate_to_human(
            reason="Needs a human.",
            summary="Escalation test.",
            db=db,
        )
        assert result.status == "escalated"
        assert result.priority == "high"

    def test_escalation_custom_priority(self, db):
        result = escalate_to_human(
            reason="Urgent legal matter.",
            summary="Legal escalation.",
            priority="urgent",
            db=db,
        )
        assert result.priority == "urgent"
        assert result.status == "escalated"
