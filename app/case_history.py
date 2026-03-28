"""
Persistence helpers for customer case history and audit views.
"""

from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from dotenv import load_dotenv

load_dotenv()


def _to_primitive(value: Any) -> Any:
    """Convert LangGraph state values into JSON-serializable primitives."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _to_primitive(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_primitive(item) for item in value]
    if hasattr(value, "content") and hasattr(value, "type"):
        return {
            "role": getattr(value, "type", "unknown"),
            "content": getattr(value, "content", ""),
        }
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def extract_conversation(messages: list[Any] | None) -> list[dict[str, str]]:
    """Keep only customer+ai messages for case-history rendering."""
    if not messages:
        return []

    conversation: list[dict[str, str]] = []
    for msg in messages:
        role = None
        content = ""

        if isinstance(msg, dict):
            role = str(msg.get("role", "")).lower()
            content = str(msg.get("content", ""))
        else:
            role = str(getattr(msg, "type", "")).lower()
            content = str(getattr(msg, "content", ""))

        if role in {"human", "user"}:
            conversation.append({"role": "customer", "content": content})
        elif role in {"ai", "assistant"}:
            conversation.append({"role": "ai", "content": content})

    return conversation


def derive_status_and_actions(state: dict[str, Any]) -> tuple[str, str | None, str | None, str | None]:
    """Derive table-friendly status and action fields from graph state."""
    review_status = str(_to_primitive(state.get("review_status")) or "").lower()
    draft_scenario = str(_to_primitive(state.get("draft_scenario")) or "").lower()
    decision_action = _to_primitive(state.get("decision_action"))
    confidence_raw = state.get("confidence_score")
    admin_feedback = state.get("admin_feedback")

    try:
        confidence = float(confidence_raw) if confidence_raw is not None else None
    except (TypeError, ValueError):
        confidence = None

    if review_status in {"approved", "rejected"}:
        status = "closed"
    elif draft_scenario == "reply" and review_status == "pending":
        status = "in_review"
    else:
        status = "active"

    hitl_action: str | None = None
    if review_status in {"approved", "rejected"}:
        came_from_hitl = bool(admin_feedback) or (confidence is not None and confidence < 0.9)
        if came_from_hitl:
            hitl_action = review_status

    final_action: str | None = None
    if review_status in {"approved", "rejected"}:
        if confidence is not None and confidence >= 0.9:
            final_action = f"auto_{review_status}"
        else:
            final_action = f"hitl_{review_status}"
    elif review_status == "pending":
        final_action = "pending_review"

    return status, str(decision_action) if decision_action else None, hitl_action, final_action


def upsert_case_row(result_state: dict[str, Any], thread_id: str) -> None:
    """Insert/update a single case-history row by thread_id."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url or not thread_id:
        return

    status, decision_maker_action, hitl_action, final_action = derive_status_and_actions(result_state)
    order_details = result_state.get("order_details") or {}
    customer_name = order_details.get("customer_name")
    order_id = result_state.get("order_id")
    conversation = extract_conversation(result_state.get("messages"))
    graph_state_json = _to_primitive(result_state)

    query = """
    INSERT INTO customer_case_history (
        thread_id,
        status,
        customer_name,
        order_id,
        graph_state_json,
        conversation_json,
        decision_maker_action,
        hitl_action,
        final_action
    ) VALUES (
        %(thread_id)s,
        %(status)s,
        %(customer_name)s,
        %(order_id)s,
        %(graph_state_json)s,
        %(conversation_json)s,
        %(decision_maker_action)s,
        %(hitl_action)s,
        %(final_action)s
    )
    ON CONFLICT (thread_id) DO UPDATE
    SET
        status = EXCLUDED.status,
        customer_name = COALESCE(EXCLUDED.customer_name, customer_case_history.customer_name),
        order_id = COALESCE(EXCLUDED.order_id, customer_case_history.order_id),
        graph_state_json = EXCLUDED.graph_state_json,
        conversation_json = EXCLUDED.conversation_json,
        decision_maker_action = EXCLUDED.decision_maker_action,
        hitl_action = EXCLUDED.hitl_action,
        final_action = EXCLUDED.final_action,
        updated_at = NOW();
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "thread_id": thread_id,
                    "status": status,
                    "customer_name": customer_name,
                    "order_id": order_id,
                    "graph_state_json": Json(graph_state_json),
                    "conversation_json": Json(conversation),
                    "decision_maker_action": decision_maker_action,
                    "hitl_action": hitl_action,
                    "final_action": final_action,
                },
            )
        conn.commit()


def list_case_history(status: str | None = None, thread_id: str | None = None, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Fetch case-history rows for UI rendering."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return []

    clauses: list[str] = []
    params: dict[str, Any] = {"limit": max(1, min(limit, 200)), "offset": max(0, offset)}

    if status:
        clauses.append("status = %(status)s")
        params["status"] = status
    if thread_id:
        clauses.append("thread_id = %(thread_id)s")
        params["thread_id"] = thread_id

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
    SELECT
        id,
        thread_id,
        status,
        customer_name,
        order_id,
        graph_state_json,
        conversation_json,
        decision_maker_action,
        hitl_action,
        final_action,
        created_at,
        updated_at
    FROM customer_case_history
    {where_sql}
    ORDER BY updated_at DESC
    LIMIT %(limit)s OFFSET %(offset)s
    """

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return [_to_primitive(row) for row in rows]
