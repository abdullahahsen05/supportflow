from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.chat import ChatRequest


def test_chat_request_valid():
    req = ChatRequest(message="How do I cancel?")
    assert req.message == "How do I cancel?"
    assert req.k == 4


def test_chat_request_custom_k():
    req = ChatRequest(message="Hello", k=6)
    assert req.k == 6


def test_chat_request_empty_message_fails():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_k_too_large_fails():
    with pytest.raises(ValidationError):
        ChatRequest(message="Hello", k=99)


def test_chat_request_k_zero_fails():
    with pytest.raises(ValidationError):
        ChatRequest(message="Hello", k=0)
