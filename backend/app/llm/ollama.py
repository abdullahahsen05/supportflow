from __future__ import annotations

import httpx
from langchain_ollama import ChatOllama

from app.core.config import settings


def get_chat_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.OLLAMA_CHAT_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.1,
        timeout=120,
    )


def check_ollama_available() -> tuple[bool, str]:
    """
    Returns (True, "") if Ollama is running and the configured chat model is available.
    Returns (False, human-readable reason) otherwise.
    """
    try:
        resp = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        resp.raise_for_status()
    except httpx.ConnectError:
        return False, (
            f"Ollama is not available at {settings.OLLAMA_BASE_URL}. "
            "Start Ollama and ensure mistral:7b is pulled."
        )
    except Exception as exc:
        return False, f"Ollama health check failed: {exc}"

    model = settings.OLLAMA_CHAT_MODEL
    model_names = [m.get("name", "") for m in resp.json().get("models", [])]
    if model not in model_names:
        return False, (
            f"Model '{model}' is not available in Ollama. "
            f"Run: ollama pull {model}"
        )
    return True, ""
