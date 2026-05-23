from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.conversation import ConversationDetail, ConversationSummary, MessageOut, TicketBrief, ToolCallBrief
from app.services.conversation_service import get_conversation_detail, get_conversations

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[ConversationSummary]:
    rows = get_conversations(db, limit=limit)
    return [ConversationSummary(**r) for r in rows]


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    data = get_conversation_detail(db, conversation_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(
        id=data["id"],
        user_id=data["user_id"],
        status=data["status"],
        intent=data["intent"],
        sentiment=data["sentiment"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        messages=[MessageOut.model_validate(m) for m in data["messages"]],
        tickets=[TicketBrief.model_validate(t) for t in data["tickets"]],
        tool_calls=[ToolCallBrief.model_validate(tc) for tc in data["tool_calls"]],
    )
