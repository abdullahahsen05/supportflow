from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.ticket import Ticket


def get_tickets(
    db: Session,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> list[Ticket]:
    q = db.query(Ticket)
    if status:
        q = q.filter(Ticket.status == status)
    if priority:
        q = q.filter(Ticket.priority == priority)
    if category:
        q = q.filter(Ticket.category == category)
    return q.order_by(Ticket.created_at.desc()).limit(limit).all()


def get_ticket(db: Session, ticket_id: int) -> Optional[Ticket]:
    return db.get(Ticket, ticket_id)


def update_ticket(
    db: Session,
    ticket_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[int] = None,
    summary: Optional[str] = None,
) -> Optional[Ticket]:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        return None
    if status is not None:
        ticket.status = status
    if priority is not None:
        ticket.priority = priority
    if assigned_to is not None:
        ticket.assigned_to = assigned_to
    if summary is not None:
        ticket.summary = summary
    db.commit()
    db.refresh(ticket)
    return ticket
