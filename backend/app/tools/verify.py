"""
CLI verification script for Phase 6 business tools.

Usage (from backend/ with .venv active):
    python -m app.tools.verify
"""
from __future__ import annotations

import json
import sys


def _sep(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def _print_result(label: str, result) -> None:
    print(f"\n[{label}]")
    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


def main() -> None:
    from app.tools.support_tools import (
        check_payment_history,
        check_refund_eligibility,
        create_support_ticket,
        escalate_to_human,
        get_order_status,
        get_subscription_status,
        get_user_profile,
    )

    # ------------------------------------------------------------------
    _sep("1. get_order_status")
    # ------------------------------------------------------------------
    _print_result("order #1004 (shipped, TRK-CD-1004)", get_order_status("1004"))
    _print_result("order #9999 (not found)", get_order_status("9999"))

    # ------------------------------------------------------------------
    _sep("2. get_user_profile")
    # ------------------------------------------------------------------
    _print_result("ayesha@example.com", get_user_profile("ayesha@example.com"))
    _print_result("unknown@example.com", get_user_profile("unknown@example.com"))

    # ------------------------------------------------------------------
    _sep("3. get_subscription_status")
    # ------------------------------------------------------------------
    _print_result("ayesha@example.com (Pro active)", get_subscription_status("ayesha@example.com"))
    _print_result("sara@example.com (Pro past_due)", get_subscription_status("sara@example.com"))

    # ------------------------------------------------------------------
    _sep("4. check_payment_history")
    # ------------------------------------------------------------------
    _print_result("ayesha@example.com (duplicate expected)", check_payment_history("ayesha@example.com"))
    _print_result("omar@example.com (no duplicate)", check_payment_history("omar@example.com"))

    # ------------------------------------------------------------------
    _sep("5. check_refund_eligibility")
    # ------------------------------------------------------------------
    _print_result("order #1004 (shipped -> requires_review)", check_refund_eligibility("1004"))
    _print_result("order #1005 (delivered -> eligible)", check_refund_eligibility("1005"))
    _print_result("order #9999 (not found)", check_refund_eligibility("9999"))

    # ------------------------------------------------------------------
    _sep("6. create_support_ticket")
    # ------------------------------------------------------------------
    ticket_result = create_support_ticket(
        category="billing",
        priority="medium",
        summary="Customer reports unexpected charge on account.",
        user_email="ayesha@example.com",
    )
    _print_result("create ticket (billing / medium)", ticket_result)

    # ------------------------------------------------------------------
    _sep("7. escalate_to_human")
    # ------------------------------------------------------------------
    escalation_result = escalate_to_human(
        reason="Customer insists on speaking to a human agent immediately.",
        summary="Billing dispute — customer unhappy with automated response.",
        user_email="ayesha@example.com",
        category="billing",
        priority="high",
    )
    _print_result("escalate to human (high priority)", escalation_result)

    # ------------------------------------------------------------------
    _sep("SUMMARY")
    # ------------------------------------------------------------------
    print("\nAll tools executed without unhandled exceptions.")
    print(f"Ticket created:   id={ticket_result.ticket_id}  status={ticket_result.status}")
    print(f"Escalation created: id={escalation_result.ticket_id}  status={escalation_result.status}")


if __name__ == "__main__":
    main()
