"""
Policy document indexing utilities for ChromaDB.
"""

from __future__ import annotations

import os
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from app.rag.config import COLLECTION_NAME, EMBEDDING_MODEL, POLICIES_DIR, POLICY_ISSUE_MAP

_client: chromadb.ClientAPI | None = None
_collection: Any | None = None
_embedding_function: OpenAIEmbeddingFunction | None = None


def _title_from_filename(filename: str) -> str:
    base = filename.replace(".md", "").replace("_", " ")
    return " ".join(word.capitalize() for word in base.split())


def _build_issue_metadata(issue_types: list[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {"issue_types": ",".join(issue_types)}
    for issue in issue_types:
        metadata[f"issue_{issue}"] = True
    return metadata


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.EphemeralClient()
    return _client


def get_embedding_function() -> OpenAIEmbeddingFunction:
    global _embedding_function
    if _embedding_function is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for policy embeddings.")
        _embedding_function = OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name=EMBEDDING_MODEL,
        )
    return _embedding_function


def get_collection() -> Any:
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=get_embedding_function(),
        )
    return _collection


def load_policy_documents(policies_dir: str | None = None) -> list[dict[str, Any]]:
    docs_dir = policies_dir or POLICIES_DIR
    if not os.path.isdir(docs_dir):
        return []

    documents: list[dict[str, Any]] = []
    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            continue

        issue_types = POLICY_ISSUE_MAP.get(filename, [])
        metadata = {
            "source": filename,
            "title": _title_from_filename(filename),
            **_build_issue_metadata(issue_types),
        }
        documents.append(
            {
                "id": f"policy::{filename}",
                "document": content,
                "metadata": metadata,
                "source": filename,
            }
        )
    return documents


def index_policies(policies_dir: str | None = None) -> int:
    docs = load_policy_documents(policies_dir=policies_dir)
    collection = get_collection()

    existing_ids = collection.get().get("ids", [])
    if existing_ids:
        collection.delete(ids=existing_ids)

    if docs:
        collection.add(
            ids=[doc["id"] for doc in docs],
            documents=[doc["document"] for doc in docs],
            metadatas=[doc["metadata"] for doc in docs],
        )
    return len(docs)


def upsert_policy_document(file_path: str) -> str:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Policy file does not exist: {file_path}")

    filename = os.path.basename(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        raise ValueError(f"Policy file is empty: {file_path}")

    issue_types = POLICY_ISSUE_MAP.get(filename, [])
    metadata = {
        "source": filename,
        "title": _title_from_filename(filename),
        **_build_issue_metadata(issue_types),
    }
    doc_id = f"policy::{filename}"

    collection = get_collection()
    collection.upsert(ids=[doc_id], documents=[content], metadatas=[metadata])
    return doc_id


def list_indexed_policies() -> list[dict[str, Any]]:
    collection = get_collection()
    data = collection.get(include=["metadatas"])
    output: list[dict[str, Any]] = []

    for idx, doc_id in enumerate(data.get("ids", [])):
        metadata = (data.get("metadatas") or [])[idx] if data.get("metadatas") else {}
        output.append(
            {
                "id": doc_id,
                "source": metadata.get("source"),
                "title": metadata.get("title"),
                "issue_types": metadata.get("issue_types", ""),
            }
        )
    return output
