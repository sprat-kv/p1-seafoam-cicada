"""
Retriever and reranker utilities for policy RAG.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_openai import ChatOpenAI

from app.rag.config import FRAUD_ELIGIBLE_ISSUES, FRAUD_THRESHOLD, TOP_K
from app.rag.indexer import get_collection


def _score_from_distance(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + float(distance))


def _normalize_query_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    output: list[dict[str, Any]] = []
    for idx, document in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        output.append(
            {
                "content": document,
                "source": (metadata or {}).get("source", "unknown"),
                "title": (metadata or {}).get("title", "Unknown Policy"),
                "relevance_score": _score_from_distance(distance),
                "metadata": metadata or {},
            }
        )
    return output


def _dedupe_by_source(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for item in items:
        source = item.get("source", "unknown")
        if source not in seen or item.get("relevance_score", 0.0) > seen[source].get("relevance_score", 0.0):
            seen[source] = item
    return list(seen.values())


def _needs_fraud_policy(issue_type: str | None, order_details: dict[str, Any] | None) -> bool:
    if issue_type not in FRAUD_ELIGIBLE_ISSUES:
        return False
    amount = (order_details or {}).get("total_amount", 0) or 0
    try:
        return float(amount) > FRAUD_THRESHOLD
    except (TypeError, ValueError):
        return False


def query_policies(
    issue_type: str | None,
    query_text: str,
    order_details: dict[str, Any] | None = None,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    collection = get_collection()
    results: list[dict[str, Any]] = []
    include_fraud = _needs_fraud_policy(issue_type, order_details)

    if issue_type:
        issue_where = {f"issue_{issue_type}": True}
        filtered = collection.query(
            query_texts=[query_text],
            where=issue_where,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        results.extend(_normalize_query_result(filtered))

    # Semantic fallback across all policies helps capture cross-cutting rules.
    semantic = collection.query(
        query_texts=[query_text],
        n_results=max(top_k, 5),
        include=["documents", "metadatas", "distances"],
    )
    results.extend(_normalize_query_result(semantic))

    if include_fraud:
        fraud = collection.get(
            where={"source": "fraud_policy.md"},
            include=["documents", "metadatas"],
        )
        docs = fraud.get("documents", []) or []
        metas = fraud.get("metadatas", []) or []
        if docs:
            results.append(
                {
                    "content": docs[0],
                    "source": (metas[0] or {}).get("source", "fraud_policy.md"),
                    "title": (metas[0] or {}).get("title", "Fraud Policy"),
                    "relevance_score": 1.0,
                    "metadata": metas[0] or {},
                }
            )

    deduped = _dedupe_by_source(results)
    if not include_fraud:
        deduped = [item for item in deduped if item.get("source") != "fraud_policy.md"]
    deduped.sort(key=lambda item: item.get("relevance_score", 0.0), reverse=True)
    return deduped[: max(top_k, 3)]


def rerank_with_llm(
    query: str,
    results: list[dict[str, Any]],
    issue_context: str,
    top_n: int = TOP_K,
) -> list[dict[str, Any]]:
    if not results:
        return []

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    candidates = []
    for idx, item in enumerate(results):
        content = item.get("content", "")
        candidates.append(
            {
                "index": idx,
                "source": item.get("source"),
                "content": content[:500],
            }
        )

    prompt = f"""
You are ranking policy snippets for customer-support action validation.

Issue context: {issue_context}
Query: {query}

Candidates (JSON):
{json.dumps(candidates, ensure_ascii=True)}

Return JSON with this schema only:
{{
  "ranked_indexes": [int, int, ...]
}}

Rules:
- Put most relevant first.
- Include at most {top_n} indexes.
- Only include indexes that exist.
"""
    raw = llm.invoke(prompt).content.strip()
    try:
        parsed = json.loads(raw)
        ranked = parsed.get("ranked_indexes", [])
    except json.JSONDecodeError:
        return results[:top_n]

    reindexed: list[dict[str, Any]] = []
    used = set()
    for idx in ranked:
        if isinstance(idx, int) and 0 <= idx < len(results) and idx not in used:
            reindexed.append(results[idx])
            used.add(idx)
    if not reindexed:
        return results[:top_n]
    return reindexed[:top_n]
