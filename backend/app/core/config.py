from __future__ import annotations

import json
from typing import Annotated, Any

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "SupportFlow AI"
    APP_ENV: str = "development"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    FRONTEND_URL: str = "http://localhost:3000"

    # Accept a JSON array string or a comma-separated string from the env file.
    # Example .env values:
    #   BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]
    #   BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:3001
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database (Phase 2+)
    DATABASE_URL: str = "postgresql+psycopg://supportflow:supportflow@localhost:5433/supportflow"

    # Ollama (Phase 4+)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "mistral:7b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # ChromaDB (Phase 4+)
    CHROMA_COLLECTION: str = "supportflow_knowledge_base"

    # MLflow (Phase 11)
    MLFLOW_TRACKING_URI: str = "file:../mlruns"
    MLFLOW_EXPERIMENT_NAME: str = "supportflow-ai-chat"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
