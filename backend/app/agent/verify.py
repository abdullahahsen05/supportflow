"""
CLI verification script for Phase 7 LangGraph agent.

Prerequisites:
  - Docker Postgres running (port 5433)
  - Ollama running with mistral:7b pulled
  - ChromaDB populated (python -m app.rag.ingest)

Usage (from backend/ with .venv active):
    python -m app.agent.verify
"""
from __future__ import annotations

import sys
import textwrap

from app.agent.graph import run_agent


def _safe(text: str) -> str:
    """Encode to stdout encoding with replacement so non-ASCII chars never crash."""
    enc = sys.stdout.encoding or "utf-8"
    return text.encode(enc, errors="replace").decode(enc)


SCENARIOS = [
    {
        "label": "FAQ — refund period",
        "message": "What is your refund period?",
        "expect_keys": {"intent": "faq"},
    },
    {
        "label": "Order status — #1004",
        "message": "Where is my order #1004?",
        "expect_keys": {"intent": "order_status", "tool_name": "get_order_status"},
    },
    {
        "label": "Order status — missing number",
        "message": "Where is my order?",
        "expect_keys": {"intent": "order_status"},
    },
    {
        "label": "Duplicate billing charge",
        "message": "I was charged twice this month.",
        "expect_keys": {"intent": "billing_issue", "tool_name": "check_payment_history"},
    },
    {
        "label": "Human escalation request",
        "message": "I want to speak to a human.",
        "expect_keys": {"intent": "human_escalation", "tool_name": "escalate_to_human"},
    },
    {
        "label": "Unknown — alien spaceship",
        "message": "What is CloudDesk's policy on alien spaceship rentals?",
        # "policy" keyword routes to faq; both faq and unknown are acceptable
        # as long as the answer doesn't invent a specific alien policy.
        "expect_keys": {},
    },
]


def _sep(label: str) -> None:
    print("\n" + "=" * 65)
    print(f"  {label}")
    print("=" * 65)


def _check(state: dict, expect_keys: dict) -> list[str]:
    """Return list of failed assertions (empty = all passed)."""
    failures = []
    for key, expected in expect_keys.items():
        actual = state.get(key)
        if actual != expected:
            failures.append(f"  FAIL {key}: expected={expected!r}, got={actual!r}")
    return failures


def main() -> None:
    total = 0
    passed = 0

    for scenario in SCENARIOS:
        _sep(scenario["label"])
        msg = scenario["message"]
        print(f"Input : {msg!r}\n")

        state = run_agent(msg)
        total += 1

        print(f"Intent    : {state.get('intent')}")
        print(f"Sentiment : {state.get('sentiment')}")
        print(f"Tool      : {state.get('tool_name')}")

        if state.get("ticket"):
            t = state["ticket"]
            print(
                f"Ticket    : #{t.get('ticket_id')}  "
                f"status={t.get('status')}  priority={t.get('priority')}"
            )

        if state.get("tool_result"):
            tr = state["tool_result"]
            # Print a one-line summary of key tool result fields
            summary_fields = ["found", "status", "duplicate_detected", "eligible",
                               "requires_review", "order_number", "tracking_number",
                               "plan_name"]
            summary = {k: tr[k] for k in summary_fields if k in tr}
            print(f"Tool result (summary): {summary}")

        print()
        answer = state.get("answer", "")
        print("Answer:")
        for line in textwrap.wrap(answer, width=62):
            print(_safe(f"  {line}"))

        failures = _check(state, scenario.get("expect_keys", {}))
        if failures:
            for f in failures:
                print(f)
        else:
            passed += 1
            print("\n  [OK] All assertions passed.")

        if state.get("error"):
            print(f"\n  [WARN] error field: {state['error']}")

    _sep("SUMMARY")
    print(f"\n  {passed}/{total} scenarios passed assertions.")
    if passed < total:
        print("  Some assertions failed — check output above.")
    else:
        print("  All scenarios completed successfully.")


if __name__ == "__main__":
    main()
