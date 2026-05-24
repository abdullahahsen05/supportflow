"""
MLflow tracking for SupportFlow AI chat interactions.

Every POST /api/chat call logs one MLflow run containing:
  Params  : model, prompt_version, intent, sentiment, tool_name
  Metrics : latency_seconds, answer_length, retrieved_source_count, confidence
  Tags    : conversation_id, ticket_created, escalated
  Artifacts: user_message.txt, answer.txt, sources.json, tool_result.json, error.txt

Tracking URI default: file:../mlruns  (repo-root/mlruns when run from backend/)
Experiment name    : supportflow-ai-chat

All logging is wrapped in try/except — a failure here NEVER breaks /api/chat.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1-agent-rag-tools"


def log_chat_run(
    *,
    model: str,
    user_message: str,
    answer: str,
    intent: Optional[str],
    sentiment: Optional[str],
    confidence: Optional[float],
    tool_name: Optional[str],
    tool_result: Optional[dict[str, Any]],
    sources: list[dict[str, Any]],
    latency_seconds: float,
    conversation_id: int,
    ticket_id: Optional[int],
    escalated: bool,
    error: Optional[str],
) -> None:
    """Log a single chat interaction as an MLflow run. Never raises."""
    try:
        import mlflow  # lazy — graceful if unavailable

        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)

        with mlflow.start_run():
            # ── Params (small string values) ──────────────────────────────
            mlflow.log_params({
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "intent": intent or "unknown",
                "sentiment": sentiment or "neutral",
                "tool_name": tool_name or "none",
            })

            # ── Metrics (numeric values) ──────────────────────────────────
            metrics: dict[str, float] = {
                "latency_seconds": latency_seconds,
                "answer_length": float(len(answer)),
                "retrieved_source_count": float(len(sources)),
            }
            if confidence is not None:
                metrics["confidence"] = float(confidence)
            mlflow.log_metrics(metrics)

            # ── Tags ──────────────────────────────────────────────────────
            mlflow.set_tags({
                "conversation_id": str(conversation_id),
                "ticket_created": str(ticket_id is not None).lower(),
                "escalated": str(escalated).lower(),
            })

            # ── Artifacts ─────────────────────────────────────────────────
            mlflow.log_text(user_message, "user_message.txt")
            mlflow.log_text(answer, "answer.txt")

            if sources:
                mlflow.log_text(json.dumps(sources, indent=2), "sources.json")

            if tool_result:
                # Exclude potentially large list fields to avoid huge artifacts
                summary = {
                    k: v
                    for k, v in tool_result.items()
                    if not isinstance(v, list) or len(v) <= 5
                }
                mlflow.log_text(json.dumps(summary, indent=2), "tool_result.json")

            if error:
                mlflow.log_text(error, "error.txt")

    except Exception as exc:
        logger.warning("MLflow logging failed (non-fatal): %s", exc)
