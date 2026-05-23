"""
Seed script for SupportFlow AI — CloudDesk fake company data.

Usage (from backend/ with .venv active):
    python -m app.db.seed

Idempotent: safe to run multiple times — existing rows are skipped.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

# Allow running as a module from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.knowledge_document import KnowledgeDocument
from app.models.order import Order
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_or_create(db: Session, model, filter_by: dict, defaults: dict):
    """Return (instance, created:bool). Never duplicates on unique filter_by key."""
    obj = db.query(model).filter_by(**filter_by).first()
    if obj is None:
        obj = model(**{**filter_by, **defaults})
        db.add(obj)
        db.flush()
        return obj, True
    return obj, False


def ts(*args) -> datetime:
    """Shorthand for UTC datetime."""
    return datetime(*args, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_users(db: Session) -> dict[str, User]:
    print("\n[users]")
    specs = [
        ("Ayesha Khan",    "ayesha@example.com",          "customer"),
        ("Omar Ali",       "omar@example.com",             "customer"),
        ("Sara Ahmed",     "sara@example.com",             "customer"),
        ("Hamza Support",  "hamza.support@clouddesk.test", "agent"),
        ("Admin User",     "admin@clouddesk.test",         "admin"),
    ]
    users: dict[str, User] = {}
    for name, email, role in specs:
        user, created = get_or_create(
            db, User,
            filter_by={"email": email},
            defaults={"name": name, "role": role},
        )
        users[email] = user
        status = "created" if created else "exists"
        print(f"  [{status}] {role:8s}  {name} <{email}>  id={user.id}")
    return users


def seed_orders(db: Session, users: dict[str, User]) -> dict[str, Order]:
    print("\n[orders]")
    ayesha = users["ayesha@example.com"]
    omar   = users["omar@example.com"]
    sara   = users["sara@example.com"]

    specs = [
        # (user, order_number, status, tracking, amount, estimated_delivery)
        (ayesha, "1004", "shipped",    "TRK-CD-1004", 149.99, ts(2026, 6, 5)),
        (omar,   "1005", "delivered",  "TRK-CD-1005",  99.99, ts(2026, 5, 10)),
        (sara,   "1006", "processing", None,           249.99, None),
        (ayesha, "1007", "cancelled",  None,            49.99, None),
        (omar,   "1008", "pending",    None,           189.99, ts(2026, 6, 15)),
    ]
    orders: dict[str, Order] = {}
    for user, order_number, status, tracking, amount, delivery in specs:
        order, created = get_or_create(
            db, Order,
            filter_by={"order_number": order_number},
            defaults={
                "user_id":           user.id,
                "status":            status,
                "tracking_number":   tracking,
                "total_amount":      amount,
                "estimated_delivery": delivery,
            },
        )
        orders[order_number] = order
        status_tag = "created" if created else "exists"
        print(f"  [{status_tag}] #{order_number}  {status:10s}  ${amount}  user={user.email}")
    return orders


def seed_subscriptions(db: Session, users: dict[str, User]) -> dict[str, Subscription]:
    print("\n[subscriptions]")
    ayesha = users["ayesha@example.com"]
    omar   = users["omar@example.com"]
    sara   = users["sara@example.com"]

    specs = [
        # (user, plan, status, renewal, billing)
        (ayesha, "Pro",     "active",   ts(2026, 6, 1),  79.99),
        (omar,   "Starter", "active",   ts(2026, 6, 15), 29.99),
        (sara,   "Pro",     "past_due", ts(2026, 5, 30), 79.99),
    ]
    subs: dict[str, Subscription] = {}
    for user, plan, status, renewal, billing in specs:
        sub, created = get_or_create(
            db, Subscription,
            # One subscription per user — use user_id+plan_name as identity
            filter_by={"user_id": user.id, "plan_name": plan},
            defaults={
                "status":         status,
                "renewal_date":   renewal,
                "billing_amount": billing,
            },
        )
        subs[user.email] = sub
        tag = "created" if created else "exists"
        print(f"  [{tag}] {user.email:35s}  {plan:7s}  {status:8s}  ${billing}/mo  id={sub.id}")
    return subs


def seed_payments(db: Session, users: dict[str, User], subs: dict[str, Subscription]) -> None:
    print("\n[payments]")
    ayesha = users["ayesha@example.com"]
    omar   = users["omar@example.com"]
    sara   = users["sara@example.com"]
    ayesha_sub = subs["ayesha@example.com"]
    omar_sub   = subs["omar@example.com"]
    sara_sub   = subs["sara@example.com"]

    specs = [
        # (user, sub, amount, status, payment_date, txn_ref)
        # Ayesha: TWO successful payments same amount same month (duplicate charge demo)
        (ayesha, ayesha_sub, 79.99, "success", ts(2026, 5, 1),  "TXN-AYE-001"),
        (ayesha, ayesha_sub, 79.99, "success", ts(2026, 5, 3),  "TXN-AYE-002"),  # duplicate!
        # Omar: one normal payment
        (omar,   omar_sub,   29.99, "success", ts(2026, 5, 15), "TXN-OMR-001"),
        # Sara: one failed payment (card declined)
        (sara,   sara_sub,   79.99, "failed",  ts(2026, 5, 30), "TXN-SAR-001"),
    ]
    for user, sub, amount, status, pay_date, txn_ref in specs:
        payment, created = get_or_create(
            db, Payment,
            filter_by={"transaction_reference": txn_ref},
            defaults={
                "user_id":         user.id,
                "subscription_id": sub.id,
                "amount":          amount,
                "status":          status,
                "payment_date":    pay_date,
            },
        )
        tag = "created" if created else "exists"
        note = "  <-- duplicate charge demo" if txn_ref == "TXN-AYE-002" else ""
        print(f"  [{tag}] {txn_ref}  {status:7s}  ${amount}  {user.email}{note}")


def seed_knowledge_documents(db: Session) -> None:
    print("\n[knowledge_documents]")
    # Paths are relative to the repo root (how they'll be read by the ingest script).
    docs = [
        ("Refund Policy",        "data/knowledge_base/refund_policy.md",       "policy"),
        ("Subscription Policy",  "data/knowledge_base/subscription_policy.md", "policy"),
        ("Shipping Policy",      "data/knowledge_base/shipping_policy.md",     "policy"),
        ("Billing Policy",       "data/knowledge_base/billing_policy.md",      "policy"),
        ("Account Setup",        "data/knowledge_base/account_setup.md",       "guide"),
        ("Troubleshooting",      "data/knowledge_base/troubleshooting.md",     "guide"),
        ("Pricing",              "data/knowledge_base/pricing.md",             "pricing"),
        ("Terms of Service",     "data/knowledge_base/terms.md",               "legal"),
    ]
    for title, file_path, doc_type in docs:
        doc, created = get_or_create(
            db, KnowledgeDocument,
            filter_by={"file_path": file_path},
            defaults={
                "title":         title,
                "document_type": doc_type,
                "indexed":       False,
            },
        )
        tag = "created" if created else "exists"
        print(f"  [{tag}] {doc_type:7s}  {title:22s}  indexed={doc.indexed}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(db: Session) -> None:
    from sqlalchemy import func, text
    print("\n" + "=" * 55)
    print("  DATABASE COUNTS")
    print("=" * 55)
    counts = {
        "users":               db.query(User).count(),
        "orders":              db.query(Order).count(),
        "subscriptions":       db.query(Subscription).count(),
        "payments":            db.query(Payment).count(),
        "knowledge_documents": db.query(KnowledgeDocument).count(),
    }
    for table, count in counts.items():
        print(f"  {table:25s} {count:>4d} rows")
    print("=" * 55)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def seed() -> None:
    print("SupportFlow AI — Seeding CloudDesk demo data")
    print("=" * 55)

    db = SessionLocal()
    try:
        users = seed_users(db)
        orders = seed_orders(db, users)
        subs   = seed_subscriptions(db, users)
        seed_payments(db, users, subs)
        seed_knowledge_documents(db)

        db.commit()
        print("\n[OK] Seed complete -- all changes committed.")
        print_summary(db)
    except Exception:
        db.rollback()
        print("\n[FAIL] Seed failed -- transaction rolled back.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
