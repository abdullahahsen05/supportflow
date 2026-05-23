from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    sender: str
    content: str
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketBrief(BaseModel):
    id: int
    status: str
    priority: str
    category: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolCallBrief(BaseModel):
    id: int
    tool_name: str
    success: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: int
    user_id: Optional[int] = None
    status: str
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    latest_message_preview: Optional[str] = None


class ConversationDetail(BaseModel):
    id: int
    user_id: Optional[int] = None
    status: str
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []
    tickets: list[TicketBrief] = []
    tool_calls: list[ToolCallBrief] = []
