"""
Conversation persistence helpers for Phase 8.

All functions accept an open SQLAlchemy Session.  They flush (not commit)
so the caller can group everything into a single commit.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.tool_call import ToolCall
from app.models.user import User


def get_or_create_conversation(
    db: Session,
    conversation_id: Optional[int] = None,
    user_email: Optional[str] = None,
) -> Conversation:
    """
    Return an existing Conversation by ID, or create a new one.

    If conversation_id is given but not found, a new conversation is created
    (graceful degradation rather than a 404 mid-request).
    """
    if conversation_id is not None:
        conv = db.get(Conversation, conversation_id)
        if conv is not None:
            return conv

    user_id: Optional[int] = None
    if user_email:
        user = db.query(User).filter(User.email == user_email).first()
        if user:
            user_id = user.id

    conv = Conversation(user_id=user_id, status="open")
    db.add(conv)
    db.flush()
    return conv


def save_message(
    db: Session,
    conversation_id: int,
    sender: str,
    content: str,
    metadata: Optional[dict] = None,
) -> Message:
    """Insert a message row and flush to get its id."""
    msg = Message(
        conversation_id=conversation_id,
        sender=sender,
        content=content,
        metadata_json=metadata,
    )
    db.add(msg)
    db.flush()
    return msg


def save_tool_call(
    db: Session,
    conversation_id: int,
    tool_name: str,
    tool_input: Optional[dict] = None,
    tool_result: Optional[dict] = None,
) -> ToolCall:
    """Persist a tool invocation record."""
    tc = ToolCall(
        conversation_id=conversation_id,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_result,
        success=True,
    )
    db.add(tc)
    db.flush()
    return tc


def link_ticket_to_conversation(
    db: Session,
    ticket_id: int,
    conversation_id: int,
) -> None:
    """Set ticket.conversation_id if it is currently NULL."""
    ticket = db.get(Ticket, ticket_id)
    if ticket and ticket.conversation_id is None:
        ticket.conversation_id = conversation_id
        db.flush()


def update_conversation_meta(
    db: Session,
    conversation_id: int,
    status: str,
    intent: Optional[str] = None,
    sentiment: Optional[str] = None,
) -> None:
    """Update status / intent / sentiment on the conversation row."""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return
    conv.status = status
    if intent:
        conv.intent = intent
    if sentiment:
        conv.sentiment = sentiment
    db.flush()


def get_conversations(db: Session, limit: int = 20) -> list[dict]:
    """Return recent conversations with latest-message preview."""
    convs = (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for conv in convs:
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        preview = (last_msg.content[:120] + "…") if last_msg and len(last_msg.content) > 120 else (last_msg.content if last_msg else None)
        result.append(
            {
                "id": conv.id,
                "user_id": conv.user_id,
                "status": conv.status,
                "intent": conv.intent,
                "sentiment": conv.sentiment,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "latest_message_preview": preview,
            }
        )
    return result


def get_conversation_detail(db: Session, conversation_id: int) -> Optional[dict]:
    """Return full conversation with messages, tickets, and tool calls."""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return None

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    tickets = (
        db.query(Ticket)
        .filter(Ticket.conversation_id == conversation_id)
        .order_by(Ticket.created_at)
        .all()
    )
    tool_calls = (
        db.query(ToolCall)
        .filter(ToolCall.conversation_id == conversation_id)
        .order_by(ToolCall.created_at)
        .all()
    )

    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "status": conv.status,
        "intent": conv.intent,
        "sentiment": conv.sentiment,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": messages,
        "tickets": tickets,
        "tool_calls": tool_calls,
    }
