from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TicketOut(BaseModel):
    id: int
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None
    category: Optional[str] = None
    priority: str
    status: str
    summary: Optional[str] = None
    escalation_reason: Optional[str] = None
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None
    summary: Optional[str] = None
