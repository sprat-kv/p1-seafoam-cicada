"""
LangGraph nodes that implement Agentic RAG for policy checks.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI

from app.graph.state import GraphState
from app.rag.config import KNOWN_ISSUE_TYPES, TOP_K
from app.rag.retriever import query_policies, rerank_with_llm
from app.schema import DraftScenario

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _llm


def _extract_first_rule_line(content: str) -> str:
    for line in content.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("#"):
            continue
        return cleaned
    return content.strip()[:160]


def _safe_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def kb_orchestrator(state: GraphState) -> dict[str, Any]:
    """
    Plan retrieval strategy and fetch policy citations for the current action.
    """
    issue_type = state.get("issue_type")
    scenario = state.get("draft_scenario")
    if scenario != DraftScenario.REPLY:
        return {"policy_citations": [], "sender": "kb_orchestrator"}

    suggested_action = state.get("suggested_action", "")
    ticket_text = state.get("ticket_text", "")
    order_details = state.get("order_details") or {}

    query_text = f"Issue type: {issue_type}\nTicket: {ticket_text}\nProposed action: {suggested_action}"
    try:
        citations = query_policies(
            issue_type=issue_type,
            query_text=query_text,
            order_details=order_details,
            top_k=TOP_K,
        )

        if len(citations) > TOP_K:
            context = f"issue_type={issue_type}; amount={order_details.get('total_amount', 'N/A')}"
            citations = rerank_with_llm(
                query=query_text,
                results=citations,
                issue_context=context,
                top_n=TOP_K,
            )
    except Exception:
        citations = []

    return {
        "policy_citations": citations,
        "sender": "kb_orchestrator",
    }


def policy_evaluator(state: GraphState) -> dict[str, Any]:
    """
    Evaluate proposed action against retrieved policies and attach citations.
    """
    citations = state.get("policy_citations") or []
    suggested_action = state.get("suggested_action", "")
    issue_type = state.get("issue_type", "unknown")
    order_details = state.get("order_details") or {}

    if not citations:
        return {
            "policy_evaluation": "No policy citations were available for this issue.",
            "applied_policies": [],
            "sender": "policy_evaluator",
        }

    payload = []
    for item in citations:
        payload.append(
            {
                "source": item.get("source"),
                "title": item.get("title"),
                "content": item.get("content", "")[:700],
            }
        )

    prompt = f"""
You are a policy compliance checker for customer support decisions.

Issue type: {issue_type}
Order summary JSON: {json.dumps(order_details, ensure_ascii=True)}
Proposed action: {suggested_action}
Retrieved policy snippets JSON: {json.dumps(payload, ensure_ascii=True)}

Return STRICT JSON only:
{{
  "policy_evaluation": "short paragraph that states if action is compliant and why",
  "applied_policies": [
    {{
      "source": "policy file name",
      "title": "readable policy title",
      "cited_rule": "exact or near-exact rule sentence used",
      "compliance": "compliant|non_compliant|requires_review"
    }}
  ]
}}
"""

    try:
        parsed = _safe_json_object(_get_llm().invoke(prompt).content.strip())
    except Exception:
        parsed = {}
    applied_policies = parsed.get("applied_policies", [])
    policy_evaluation = parsed.get("policy_evaluation")

    if not isinstance(applied_policies, list) or not applied_policies:
        fallback = []
        for item in citations:
            fallback.append(
                {
                    "source": item.get("source", "unknown"),
                    "title": item.get("title", "Unknown Policy"),
                    "cited_rule": _extract_first_rule_line(item.get("content", "")),
                    "compliance": "requires_review",
                }
            )
        applied_policies = fallback

    if not isinstance(policy_evaluation, str) or not policy_evaluation.strip():
        policy_evaluation = "Policy review completed. See applied_policies for cited rules."

    cited_policy_names = ", ".join(
        sorted({policy.get("source", "unknown") for policy in applied_policies})
    )
    enriched_action = (
        f"{suggested_action}\n\n"
        f"Policy evaluation: {policy_evaluation}\n"
        f"Applied policies: {cited_policy_names}"
    )

    return {
        "suggested_action": enriched_action,
        "policy_evaluation": policy_evaluation,
        "applied_policies": applied_policies,
        "sender": "policy_evaluator",
    }
