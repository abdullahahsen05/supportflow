"""
Pydantic result schemas for SupportFlow business tools.

Each schema is the return type of one tool function.
All schemas include a `found` field for tools that do a primary lookup,
and a `message` field for human-readable status.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared sub-schema
# ---------------------------------------------------------------------------

class PaymentRecord(BaseModel):
    amount: float
    status: str
    payment_date: datetime
    transaction_reference: Optional[str]


# ---------------------------------------------------------------------------
# Tool result schemas
# ---------------------------------------------------------------------------

class OrderStatusResult(BaseModel):
    found: bool
    order_number: Optional[str] = None
    status: Optional[str] = None
    tracking_number: Optional[str] = None
    total_amount: Optional[float] = None
    estimated_delivery: Optional[datetime] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    message: str


class UserProfileResult(BaseModel):
    found: bool
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    message: str


class SubscriptionStatusResult(BaseModel):
    found: bool
    plan_name: Optional[str] = None
    status: Optional[str] = None
    renewal_date: Optional[datetime] = None
    billing_amount: Optional[float] = None
    message: str


class PaymentHistoryResult(BaseModel):
    found: bool
    payments: list[PaymentRecord] = []
    duplicate_detected: bool = False
    duplicate_details: Optional[str] = None
    message: str


class RefundEligibilityResult(BaseModel):
    found: bool
    order_number: Optional[str] = None
    order_status: Optional[str] = None
    eligible: Optional[bool] = None        # None means "requires review"
    requires_review: bool = False
    explanation: str


class TicketResult(BaseModel):
    ticket_id: int
    status: str
    priority: str
    category: Optional[str]
    summary: Optional[str]
    message: str


class EscalationResult(BaseModel):
    ticket_id: int
    status: str
    priority: str
    reason: str
    message: str
