from __future__ import annotations

from app.llm.prompts import build_context


def test_build_context_empty():
    assert build_context([]) == ""


def test_build_context_single_chunk():
    chunks = [{"title": "Refund Policy", "text": "30-day refund window.", "source": "refund_policy.md"}]
    result = build_context(chunks)
    assert "[Source: Refund Policy]" in result
    assert "30-day refund window." in result


def test_build_context_multiple_chunks():
    chunks = [
        {"title": "Refund Policy", "text": "30-day window.", "source": "refund_policy.md"},
        {"title": "Shipping Policy", "text": "Ships in 3 days.", "source": "shipping_policy.md"},
    ]
    result = build_context(chunks)
    assert "---" in result
    assert "[Source: Refund Policy]" in result
    assert "[Source: Shipping Policy]" in result


def test_build_context_falls_back_to_source_when_no_title():
    chunks = [{"title": "", "source": "billing_policy.md", "text": "Billing info."}]
    result = build_context(chunks)
    assert "billing_policy.md" in result
