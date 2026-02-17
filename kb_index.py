"""
CLI for indexing and inspecting the policy knowledge base.
"""

from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

from app.rag import index_policies, list_indexed_policies, query_policies, upsert_policy_document
from app.rag.config import POLICIES_DIR

# Ensure CLI picks up OPENAI_API_KEY and other env vars from .env.
load_dotenv()


def cmd_index(args: argparse.Namespace) -> None:
    policies_dir = args.policies_dir or POLICIES_DIR
    count = index_policies(policies_dir=policies_dir)
    print(f"Indexed {count} policy documents from: {policies_dir}")


def cmd_add(args: argparse.Namespace) -> None:
    file_path = os.path.abspath(args.file)
    doc_id = upsert_policy_document(file_path)
    print(f"Upserted document: {doc_id}")


def cmd_list(_: argparse.Namespace) -> None:
    docs = list_indexed_policies()
    if not docs:
        print("No policies are currently indexed.")
        return
    print(json.dumps(docs, indent=2))


def cmd_query(args: argparse.Namespace) -> None:
    issue_type = args.issue_type
    query_text = args.text
    result = query_policies(issue_type=issue_type, query_text=query_text, top_k=args.top_k)
    print(json.dumps(result, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Policy KB index and query tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Index all policy docs")
    p_index.add_argument("--policies-dir", default=POLICIES_DIR, help="Path to policies directory")
    p_index.set_defaults(func=cmd_index)

    p_add = sub.add_parser("add", help="Add or update a single policy doc")
    p_add.add_argument("--file", required=True, help="Path to markdown policy file")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List indexed policy docs")
    p_list.set_defaults(func=cmd_list)

    p_query = sub.add_parser("query", help="Run a retrieval query against the KB")
    p_query.add_argument("--text", required=True, help="Query text")
    p_query.add_argument("--issue-type", default=None, help="Issue type for filtered retrieval")
    p_query.add_argument("--top-k", type=int, default=3, help="Number of results")
    p_query.set_defaults(func=cmd_query)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
