from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ticket import TicketOut, TicketUpdate
from app.services.ticket_service import get_ticket, get_tickets, update_ticket

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


@router.get("", response_model=list[TicketOut])
def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[TicketOut]:
    tickets = get_tickets(db, status=status, priority=priority, category=category, limit=limit)
    return [TicketOut.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
) -> TicketOut:
    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketOut.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketOut)
def patch_ticket(
    ticket_id: int,
    body: TicketUpdate,
    db: Session = Depends(get_db),
) -> TicketOut:
    ticket = update_ticket(
        db,
        ticket_id,
        status=body.status,
        priority=body.priority,
        assigned_to=body.assigned_to,
        summary=body.summary,
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketOut.model_validate(ticket)
