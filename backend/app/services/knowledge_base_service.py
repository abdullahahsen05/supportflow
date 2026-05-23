from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge_document import KnowledgeDocument


def get_documents(db: Session) -> list[KnowledgeDocument]:
    return db.query(KnowledgeDocument).order_by(KnowledgeDocument.id).all()
