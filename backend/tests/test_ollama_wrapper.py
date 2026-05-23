from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.llm.ollama import check_ollama_available, get_chat_llm


def test_get_chat_llm_returns_chat_ollama():
    llm = get_chat_llm()
    assert llm is not None
    assert hasattr(llm, "ainvoke")


def test_check_ollama_available_connect_error():
    import httpx

    with patch("app.llm.ollama.httpx.get", side_effect=httpx.ConnectError("refused")):
        ok, reason = check_ollama_available()

    assert ok is False
    assert "not available" in reason.lower() or "ollama" in reason.lower()


def test_check_ollama_available_model_missing():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"models": [{"name": "llama3:8b"}]}

    with patch("app.llm.ollama.httpx.get", return_value=mock_resp):
        ok, reason = check_ollama_available()

    assert ok is False
    assert "ollama pull" in reason


def test_check_ollama_available_success():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "models": [{"name": "mistral:7b"}, {"name": "nomic-embed-text:latest"}]
    }

    with patch("app.llm.ollama.httpx.get", return_value=mock_resp):
        ok, reason = check_ollama_available()

    assert ok is True
    assert reason == ""
