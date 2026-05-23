from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Local-first agentic customer support platform.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.health import router as health_router
    app.include_router(health_router)

    from app.api.chat import router as chat_router
    app.include_router(chat_router)

    from app.api.conversations import router as conversations_router
    app.include_router(conversations_router)

    from app.api.tickets import router as tickets_router
    app.include_router(tickets_router)

    from app.api.feedback import router as feedback_router
    app.include_router(feedback_router)

    from app.api.knowledge_base import router as knowledge_base_router
    app.include_router(knowledge_base_router)

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info(
            "SupportFlow API starting | env=%s | cors=%s",
            settings.APP_ENV,
            settings.BACKEND_CORS_ORIGINS,
        )

    return app


app = create_app()
