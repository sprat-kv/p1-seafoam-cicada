"""
Configuration and policy mappings for the RAG subsystem.
"""

import os

COLLECTION_NAME = "viridien_policies"
EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 3
FRAUD_THRESHOLD = 80.0

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
POLICIES_DIR = os.path.join(ROOT, "policies")

# Primary policy mappings by file.
POLICY_ISSUE_MAP: dict[str, list[str]] = {
    "chargeback_policy.md": ["duplicate_charge"],
    "delivery_policy.md": ["late_delivery"],
    "refund_policy.md": ["refund_request"],
    "warranty_policy.md": ["defective_product", "damaged_item"],
    # Fraud policy is intentionally conditional (amount threshold), not primary-mapped.
    "fraud_policy.md": [],
}

KNOWN_ISSUE_TYPES = {
    "refund_request",
    "duplicate_charge",
    "late_delivery",
    "defective_product",
    "damaged_item",
    "wrong_item",
    "missing_item",
}

FRAUD_ELIGIBLE_ISSUES = {"refund_request", "wrong_item", "missing_item"}
