from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.knowledge_base_service import get_documents

router = APIRouter(prefix="/api/knowledge-base", tags=["Knowledge Base"])


class KnowledgeDocumentOut(BaseModel):
    id: int
    title: str
    file_path: str
    document_type: Optional[str] = None
    indexed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReindexResponse(BaseModel):
    message: str
    cli_command: str


@router.get("", response_model=list[KnowledgeDocumentOut])
def list_knowledge_documents(
    db: Session = Depends(get_db),
) -> list[KnowledgeDocumentOut]:
    docs = get_documents(db)
    return [KnowledgeDocumentOut.model_validate(d) for d in docs]


@router.post("/reindex", response_model=ReindexResponse)
def reindex_knowledge_base() -> ReindexResponse:
    """
    Reindexing requires ChromaDB + Ollama and is a long-running operation.
    Run via CLI to avoid HTTP timeout issues.
    """
    return ReindexResponse(
        message="Reindex is available via CLI. Run the command below from backend/ with .venv active.",
        cli_command="python -m app.rag.ingest",
    )
