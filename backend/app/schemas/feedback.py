from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    conversation_id: int
    message_id: Optional[int] = None
    feedback_type: str
    comment: Optional[str] = None


class FeedbackOut(BaseModel):
    id: int
    conversation_id: int
    message_id: Optional[int] = None
    feedback_type: str
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
