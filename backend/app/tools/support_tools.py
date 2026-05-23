"""
SupportFlow AI — business tools over PostgreSQL.

Each function:
- Accepts an optional SQLAlchemy Session (db). If omitted, it creates and
  closes its own session so the tool can be called directly from scripts,
  tests, or the LangGraph agent.
- Returns a typed Pydantic schema (never raises for expected "not found" cases).
- Does NOT call the LLM.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Generator, Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.order import Order
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.ticket import Ticket
from app.models.user import User
from app.tools.schemas import (
    EscalationResult,
    OrderStatusResult,
    PaymentHistoryResult,
    PaymentRecord,
    RefundEligibilityResult,
    SubscriptionStatusResult,
    TicketResult,
    UserProfileResult,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@contextmanager
def _session(db: Optional[Session] = None) -> Generator[Session, None, None]:
    """Yield an existing session or create/close a new one."""
    if db is not None:
        yield db
    else:
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()


def _get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


# ---------------------------------------------------------------------------
# 1. get_order_status
# ---------------------------------------------------------------------------

def get_order_status(order_number: str, db: Optional[Session] = None) -> OrderStatusResult:
    """Return status info for an order identified by order_number string."""
    with _session(db) as s:
        order: Optional[Order] = (
            s.query(Order).filter(Order.order_number == order_number).first()
        )
        if order is None:
            return OrderStatusResult(
                found=False,
                message=f"Order #{order_number} not found.",
            )

        user: Optional[User] = s.query(User).filter(User.id == order.user_id).first()
        return OrderStatusResult(
            found=True,
            order_number=order.order_number,
            status=order.status,
            tracking_number=order.tracking_number,
            total_amount=float(order.total_amount),
            estimated_delivery=order.estimated_delivery,
            customer_name=user.name if user else None,
            customer_email=user.email if user else None,
            message=f"Order #{order_number} found with status '{order.status}'.",
        )


# ---------------------------------------------------------------------------
# 2. get_user_profile
# ---------------------------------------------------------------------------

def get_user_profile(email: str, db: Optional[Session] = None) -> UserProfileResult:
    """Return basic profile info for a user by email."""
    with _session(db) as s:
        user = _get_user_by_email(s, email)
        if user is None:
            return UserProfileResult(
                found=False,
                message=f"No user found with email '{email}'.",
            )
        return UserProfileResult(
            found=True,
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            message=f"User '{user.name}' found (role: {user.role}).",
        )


# ---------------------------------------------------------------------------
# 3. get_subscription_status
# ---------------------------------------------------------------------------

def get_subscription_status(email: str, db: Optional[Session] = None) -> SubscriptionStatusResult:
    """Return the subscription for a user identified by email."""
    with _session(db) as s:
        user = _get_user_by_email(s, email)
        if user is None:
            return SubscriptionStatusResult(
                found=False,
                message=f"No user found with email '{email}'.",
            )

        sub: Optional[Subscription] = (
            s.query(Subscription).filter(Subscription.user_id == user.id).first()
        )
        if sub is None:
            return SubscriptionStatusResult(
                found=False,
                message=f"User '{user.name}' has no active subscription.",
            )

        return SubscriptionStatusResult(
            found=True,
            plan_name=sub.plan_name,
            status=sub.status,
            renewal_date=sub.renewal_date,
            billing_amount=float(sub.billing_amount),
            message=(
                f"Subscription found: {sub.plan_name} plan, "
                f"status={sub.status}, renewal={sub.renewal_date}."
            ),
        )


# ---------------------------------------------------------------------------
# 4. check_payment_history
# ---------------------------------------------------------------------------

_DUPLICATE_WINDOW_DAYS = 7
_DUPLICATE_MIN_AMOUNT = 1.00


def _detect_duplicates(payments: list[Payment]) -> tuple[bool, Optional[str]]:
    """
    Detect if two successful payments of the same amount occurred within
    _DUPLICATE_WINDOW_DAYS days of each other.
    Returns (detected: bool, details: str | None).
    """
    successful = [p for p in payments if p.status == "success"]
    for i, p1 in enumerate(successful):
        for p2 in successful[i + 1 :]:
            if float(p1.amount) != float(p2.amount):
                continue
            if float(p1.amount) < _DUPLICATE_MIN_AMOUNT:
                continue
            delta = abs((p1.payment_date - p2.payment_date).days)
            if delta <= _DUPLICATE_WINDOW_DAYS:
                return True, (
                    f"Two successful payments of ${p1.amount:.2f} detected "
                    f"({p1.transaction_reference} on "
                    f"{p1.payment_date.date()} and "
                    f"{p2.transaction_reference} on "
                    f"{p2.payment_date.date()}, {delta} day(s) apart). "
                    "Possible duplicate charge."
                )
    return False, None


def check_payment_history(
    email: str, db: Optional[Session] = None
) -> PaymentHistoryResult:
    """Return recent payment history for a user and flag potential duplicates."""
    with _session(db) as s:
        user = _get_user_by_email(s, email)
        if user is None:
            return PaymentHistoryResult(
                found=False,
                message=f"No user found with email '{email}'.",
            )

        payments: list[Payment] = (
            s.query(Payment)
            .filter(Payment.user_id == user.id)
            .order_by(Payment.payment_date.desc())
            .all()
        )

        if not payments:
            return PaymentHistoryResult(
                found=True,
                payments=[],
                message=f"No payment records found for '{email}'.",
            )

        duplicate_detected, duplicate_details = _detect_duplicates(payments)

        records = [
            PaymentRecord(
                amount=float(p.amount),
                status=p.status,
                payment_date=p.payment_date,
                transaction_reference=p.transaction_reference,
            )
            for p in payments
        ]

        msg = f"{len(records)} payment(s) found for '{email}'."
        if duplicate_detected:
            msg += " WARNING: Possible duplicate charge detected."

        return PaymentHistoryResult(
            found=True,
            payments=records,
            duplicate_detected=duplicate_detected,
            duplicate_details=duplicate_details,
            message=msg,
        )


# ---------------------------------------------------------------------------
# 5. check_refund_eligibility
# ---------------------------------------------------------------------------

# Status → (eligible, requires_review, explanation)
_REFUND_RULES: dict[str, tuple[Optional[bool], bool, str]] = {
    "delivered": (
        True,
        False,
        "Order has been delivered. Refund can be requested within the refund window.",
    ),
    "shipped": (
        None,
        True,
        "Order is currently in transit. Refund eligibility requires review once delivered.",
    ),
    "processing": (
        False,
        False,
        "Order is still being processed and has not shipped yet. "
        "Please wait until the order ships before requesting a refund.",
    ),
    "pending": (
        False,
        False,
        "Order is pending and has not been fulfilled. Refund not applicable at this stage.",
    ),
    "cancelled": (
        False,
        False,
        "Order was cancelled. If a charge was made, please contact support to verify.",
    ),
}


def check_refund_eligibility(
    order_number: str, db: Optional[Session] = None
) -> RefundEligibilityResult:
    """Apply simple deterministic refund eligibility rules to an order."""
    with _session(db) as s:
        order: Optional[Order] = (
            s.query(Order).filter(Order.order_number == order_number).first()
        )
        if order is None:
            return RefundEligibilityResult(
                found=False,
                explanation=f"Order #{order_number} not found.",
            )

        status = order.status.lower()
        eligible, requires_review, explanation = _REFUND_RULES.get(
            status,
            (None, True, f"Order status '{order.status}' requires manual review."),
        )

        return RefundEligibilityResult(
            found=True,
            order_number=order.order_number,
            order_status=order.status,
            eligible=eligible,
            requires_review=requires_review,
            explanation=explanation,
        )


# ---------------------------------------------------------------------------
# 6. create_support_ticket
# ---------------------------------------------------------------------------

def create_support_ticket(
    category: str,
    priority: str,
    summary: str,
    user_email: Optional[str] = None,
    conversation_id: Optional[int] = None,
    escalation_reason: Optional[str] = None,
    db: Optional[Session] = None,
) -> TicketResult:
    """
    Insert a ticket row and return its id and details.

    Status defaults to 'open'. If escalation_reason is provided the status
    is set to 'escalated' automatically.
    """
    status = "escalated" if escalation_reason else "open"

    with _session(db) as s:
        user_id: Optional[int] = None
        if user_email:
            user = _get_user_by_email(s, user_email)
            if user:
                user_id = user.id

        ticket = Ticket(
            conversation_id=conversation_id,
            user_id=user_id,
            category=category,
            priority=priority,
            status=status,
            summary=summary,
            escalation_reason=escalation_reason,
        )
        s.add(ticket)
        s.commit()
        s.refresh(ticket)

        return TicketResult(
            ticket_id=ticket.id,
            status=ticket.status,
            priority=ticket.priority,
            category=ticket.category,
            summary=ticket.summary,
            message=(
                f"Ticket #{ticket.id} created with status='{status}', "
                f"priority='{priority}'."
            ),
        )


# ---------------------------------------------------------------------------
# 7. escalate_to_human
# ---------------------------------------------------------------------------

def escalate_to_human(
    reason: str,
    summary: str,
    user_email: Optional[str] = None,
    conversation_id: Optional[int] = None,
    category: Optional[str] = None,
    priority: str = "high",
    db: Optional[Session] = None,
) -> EscalationResult:
    """
    Create a ticket with status='escalated' to hand off to a human agent.
    """
    with _session(db) as s:
        user_id: Optional[int] = None
        if user_email:
            user = _get_user_by_email(s, user_email)
            if user:
                user_id = user.id

        ticket = Ticket(
            conversation_id=conversation_id,
            user_id=user_id,
            category=category,
            priority=priority,
            status="escalated",
            summary=summary,
            escalation_reason=reason,
        )
        s.add(ticket)
        s.commit()
        s.refresh(ticket)

        return EscalationResult(
            ticket_id=ticket.id,
            status="escalated",
            priority=priority,
            reason=reason,
            message=(
                f"Ticket #{ticket.id} escalated to human agent "
                f"(priority={priority})."
            ),
        )
