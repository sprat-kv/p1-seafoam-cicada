"""
Interactive terminal chat demo for the Ticket Triage FastAPI service.

Features:
- Multi-turn chat via /triage/invoke
- Shows RAG policy fields (policy_evaluation, applied_policies)
- Optional inline admin decision flow via /admin/review
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests


def print_json(title: str, payload: Any) -> None:
    print(f"\n{title}")
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def call_triage(base_url: str, ticket_text: str, thread_id: str | None) -> dict[str, Any]:
    body: dict[str, Any] = {"ticket_text": ticket_text}
    if thread_id:
        body["thread_id"] = thread_id
    resp = requests.post(f"{base_url}/triage/invoke", json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()


def call_admin_review(
    base_url: str,
    thread_id: str,
    status: str,
    feedback: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"action": {"status": status}}
    if feedback:
        payload["action"]["feedback"] = feedback
    resp = requests.post(
        f"{base_url}/admin/review",
        params={"thread_id": thread_id},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def render_triage_response(data: dict[str, Any]) -> None:
    print("\n--- Assistant Reply ---")
    print(data.get("draft_reply") or "(no draft reply)")

    print("\n--- Triage Status ---")
    print(f"thread_id: {data.get('thread_id')}")
    print(f"issue_type: {data.get('issue_type')}")
    print(f"draft_scenario: {data.get('draft_scenario')}")
    print(f"review_status: {data.get('review_status')}")

    policy_eval = data.get("policy_evaluation")
    if policy_eval:
        print("\n--- Policy Evaluation ---")
        print(policy_eval)

    applied_policies = data.get("applied_policies") or []
    if applied_policies:
        print("\n--- Applied Policies ---")
        for idx, policy in enumerate(applied_policies, start=1):
            source = policy.get("source", "unknown")
            title = policy.get("title", "Unknown Policy")
            cited_rule = policy.get("cited_rule", "")
            compliance = policy.get("compliance", "requires_review")
            print(f"{idx}. {title} ({source})")
            print(f"   compliance: {compliance}")
            if cited_rule:
                print(f"   cited_rule: {cited_rule}")

    suggested_action = data.get("suggested_action")
    if suggested_action:
        print("\n--- Suggested Action (Admin View) ---")
        print(suggested_action)


def choose_admin_action(default_auto_approve: bool) -> str | None:
    if default_auto_approve:
        return "approved"

    print("\nAdmin decision required. Choose:")
    print("  [a] approve")
    print("  [r] reject")
    print("  [s] skip for now")
    choice = input("> ").strip().lower()
    if choice == "a":
        return "approved"
    if choice == "r":
        return "rejected"
    return None


def repl(base_url: str, auto_approve: bool) -> int:
    thread_id: str | None = None
    print("RAG Chat Demo")
    print("Type a customer message and press Enter.")
    print("Commands: /quit, /exit, /pending")

    while True:
        try:
            user_text = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return 0

        if not user_text:
            continue
        if user_text in {"/quit", "/exit"}:
            print("Bye.")
            return 0

        if user_text == "/pending":
            resp = requests.get(f"{base_url}/admin/review", timeout=30)
            resp.raise_for_status()
            print_json("Pending tickets", resp.json())
            continue

        try:
            triage_data = call_triage(base_url, user_text, thread_id)
        except requests.HTTPError as exc:
            print(f"Request failed: {exc}")
            if exc.response is not None:
                print(exc.response.text)
            continue
        except requests.RequestException as exc:
            print(f"Request failed: {exc}")
            continue

        thread_id = triage_data.get("thread_id") or thread_id
        render_triage_response(triage_data)

        if triage_data.get("review_status") == "pending" and thread_id:
            decision = choose_admin_action(auto_approve)
            if decision is None:
                print("Skipped admin decision for now.")
                continue

            feedback = input("Admin feedback (optional)> ").strip()
            feedback_value = feedback if feedback else None
            try:
                reviewed_data = call_admin_review(
                    base_url=base_url,
                    thread_id=thread_id,
                    status=decision,
                    feedback=feedback_value,
                )
            except requests.HTTPError as exc:
                print(f"Admin review failed: {exc}")
                if exc.response is not None:
                    print(exc.response.text)
                continue
            except requests.RequestException as exc:
                print(f"Admin review failed: {exc}")
                continue

            print("\n=== Post-Review Response ===")
            render_triage_response(reviewed_data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive API chat demo for RAG triage system")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="FastAPI base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Automatically approve pending admin reviews",
    )
    args = parser.parse_args()

    return repl(base_url=args.base_url.rstrip("/"), auto_approve=args.auto_approve)


if __name__ == "__main__":
    sys.exit(main())
