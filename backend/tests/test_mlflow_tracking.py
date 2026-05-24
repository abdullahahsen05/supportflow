"""
Tests for backend/app/observability/mlflow_tracking.py

Strategy
--------
* Test 1: log_chat_run completes without raising using a real temp file-based
  tracking URI (verifies happy path with actual MLflow writes).
* Test 2: log_chat_run is silent when mlflow.start_run raises (verifies
  non-breaking behaviour when MLflow is misconfigured/unavailable).
* Test 3: log_chat_run is silent when mlflow itself cannot be imported
  (verifies graceful degradation if the package were somehow absent).

Run from backend/ with .venv active:
    pytest tests/test_mlflow_tracking.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.observability.mlflow_tracking import log_chat_run, PROMPT_VERSION


# ---------------------------------------------------------------------------
# Shared payload used across tests
# ---------------------------------------------------------------------------

_PAYLOAD = dict(
    model="mistral:7b",
    user_message="Where is my order #1004?",
    answer="Your order #1004 has shipped. Tracking: TRK-CD-1004.",
    intent="order_status",
    sentiment="neutral",
    confidence=0.85,
    tool_name="get_order_status",
    tool_result={"found": True, "order_number": "1004", "status": "shipped"},
    sources=[{"title": "Order Policy", "file_path": "orders.md", "chunk_index": 0, "distance": 0.12}],
    latency_seconds=2.34,
    conversation_id=42,
    ticket_id=None,
    escalated=False,
    error=None,
)

_ESCALATED_PAYLOAD = dict(
    model="mistral:7b",
    user_message="I was charged twice this month.",
    answer="We detected a duplicate charge and escalated your case.",
    intent="billing_issue",
    sentiment="negative",
    confidence=0.91,
    tool_name="check_payment_history",
    tool_result={"found": True, "duplicate_detected": True, "payments": []},
    sources=[],
    latency_seconds=3.11,
    conversation_id=99,
    ticket_id=7,
    escalated=True,
    error=None,
)


# ---------------------------------------------------------------------------
# Test 1: happy path — real file-based MLflow write
# ---------------------------------------------------------------------------

class TestLogChatRunHappyPath:

    def test_does_not_raise_for_faq_interaction(self, tmp_path):
        """log_chat_run writes to a temp file store without raising."""
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = f"file:{tmp_path / 'mlruns'}"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test-experiment"
            log_chat_run(**_PAYLOAD)

    def test_does_not_raise_for_escalated_interaction(self, tmp_path):
        """log_chat_run handles ticket_created=True and escalated=True without raising."""
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = f"file:{tmp_path / 'mlruns'}"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test-experiment"
            log_chat_run(**_ESCALATED_PAYLOAD)

    def test_does_not_raise_when_all_optionals_are_none(self, tmp_path):
        """log_chat_run handles all optional fields being None gracefully."""
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = f"file:{tmp_path / 'mlruns'}"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test-experiment"
            log_chat_run(
                model="mistral:7b",
                user_message="Hello",
                answer="Hi",
                intent=None,
                sentiment=None,
                confidence=None,
                tool_name=None,
                tool_result=None,
                sources=[],
                latency_seconds=0.5,
                conversation_id=1,
                ticket_id=None,
                escalated=False,
                error=None,
            )

    def test_prompt_version_constant_is_set(self):
        """PROMPT_VERSION constant is a non-empty string."""
        assert isinstance(PROMPT_VERSION, str)
        assert len(PROMPT_VERSION) > 0

    def test_does_not_raise_and_logs_error_artifact(self, tmp_path):
        """log_chat_run writes error.txt artifact when error is non-None."""
        import mlflow
        tracking_uri = f"file:{tmp_path / 'mlruns'}"
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = tracking_uri
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test-experiment"
            log_chat_run(
                model="mistral:7b",
                user_message="Test",
                answer="",
                intent=None,
                sentiment=None,
                confidence=None,
                tool_name=None,
                tool_result=None,
                sources=[],
                latency_seconds=0.1,
                conversation_id=1,
                ticket_id=None,
                escalated=False,
                error="Tool timed out after 180s",
            )

        # Verify error.txt artifact was written
        mlflow.set_tracking_uri(tracking_uri)
        client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
        experiment = client.get_experiment_by_name("test-experiment")
        assert experiment is not None
        runs = client.search_runs(experiment_ids=[experiment.experiment_id])
        assert len(runs) >= 1
        artifacts = client.list_artifacts(runs[0].info.run_id)
        artifact_names = {a.path for a in artifacts}
        assert "error.txt" in artifact_names


# ---------------------------------------------------------------------------
# Test 2: MLflow failure is swallowed — chat must not break
# ---------------------------------------------------------------------------

class TestLogChatRunNonBreaking:

    def test_silent_when_start_run_raises(self):
        """log_chat_run swallows exceptions from mlflow.start_run."""
        import mlflow as _mlflow
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = "file:/nonexistent"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test"
            with patch.object(_mlflow, "start_run", side_effect=Exception("MLflow is down")):
                log_chat_run(**_PAYLOAD)

    def test_silent_when_set_tracking_uri_raises(self):
        """log_chat_run swallows exceptions from mlflow.set_tracking_uri."""
        with patch("app.observability.mlflow_tracking.settings") as mock_settings:
            mock_settings.MLFLOW_TRACKING_URI = "file:/nonexistent"
            mock_settings.MLFLOW_EXPERIMENT_NAME = "test"
            with patch("mlflow.set_tracking_uri", side_effect=RuntimeError("URI error")):
                log_chat_run(**_PAYLOAD)

    def test_silent_when_mlflow_import_fails(self):
        """log_chat_run is a no-op if mlflow raises on import (ImportError path)."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "mlflow":
                raise ImportError("mlflow not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            log_chat_run(**_PAYLOAD)
