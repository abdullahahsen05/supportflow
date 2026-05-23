from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.feedback import Feedback


def create_feedback(
    db: Session,
    conversation_id: int,
    feedback_type: str,
    message_id: Optional[int] = None,
    comment: Optional[str] = None,
) -> Feedback:
    fb = Feedback(
        conversation_id=conversation_id,
        message_id=message_id,
        feedback_type=feedback_type,
        comment=comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb
