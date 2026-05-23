from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.conversation import Conversation
from app.schemas.feedback import FeedbackCreate, FeedbackOut
from app.services.feedback_service import create_feedback

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackOut, status_code=201)
def submit_feedback(
    body: FeedbackCreate,
    db: Session = Depends(get_db),
) -> FeedbackOut:
    # Validate conversation exists
    conv = db.get(Conversation, body.conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    fb = create_feedback(
        db,
        conversation_id=body.conversation_id,
        feedback_type=body.feedback_type,
        message_id=body.message_id,
        comment=body.comment,
    )
    return FeedbackOut.model_validate(fb)
