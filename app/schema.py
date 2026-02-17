"""
Domain models for the Ticket Triage system.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    """Status of the Admin review."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DraftScenario(str, Enum):
    """Scenario type for the unified draft node."""
    REPLY = "reply"                      # Normal issue response using template
    NEED_IDENTIFIER = "need_identifier"  # Ask for order_id or email
    ORDER_NOT_FOUND = "order_not_found"  # Order ID invalid, ask for correct info
    NO_ORDERS_FOUND = "no_orders_found"  # Email has no orders
    CONFIRM_ORDER = "confirm_order"      # Multiple orders, list options for user to pick


class RoutePath(str, Enum):
    """Routing path after ingest for multi-turn conversation support."""
    FULL = "full"              # Both missing - run full pipeline (classify + resolve)
    RECLASSIFY = "reclassify"  # Only issue missing - run classification only
    RESOLVE = "resolve"        # Only order missing - run order resolution only
    DRAFT = "draft"            # Both filled - skip to draft (no re-detection)


class ReviewAction(BaseModel):
    """Action taken by Admin during review."""
    status: ReviewStatus
    feedback: Optional[str] = Field(default=None, description="Admin feedback or suggested edits")


class OrderItem(BaseModel):
    """Item in an order."""
    sku: str
    name: str
    quantity: int


class Order(BaseModel):
    """Order details from the orders database."""
    order_id: str
    customer_name: str
    email: str
    items: list[OrderItem]
    order_date: str
    status: str
    delivery_date: Optional[str] = None
    total_amount: float
    currency: str = "USD"


class TriageInput(BaseModel):
    """Input for the triage endpoint."""
    ticket_text: str = Field(..., description="The customer's message/ticket text")
    order_id: Optional[str] = Field(default=None, description="Order ID if known")
    thread_id: Optional[str] = Field(default=None, description="Thread ID for continuing a conversation")


class TriageOutput(BaseModel):
    """Output from the triage endpoint."""
    thread_id: str
    order_id: Optional[str] = None
    email: Optional[str] = None
    issue_type: Optional[str] = None
    draft_scenario: Optional[DraftScenario] = None
    draft_reply: Optional[str] = None
    suggested_action: Optional[str] = Field(default=None, description="Template action awaiting admin approval")
    policy_evaluation: Optional[str] = Field(default=None, description="Policy compliance summary for suggested action")
    applied_policies: Optional[list[dict]] = Field(default=None, description="Policies used with cited rules for UI display")
    review_status: Optional[ReviewStatus] = None
    evidence: Optional[str] = None
    recommendation: Optional[str] = None
    candidate_orders: Optional[list[dict]] = None
    messages: list[dict] = Field(default_factory=list)
    # Backward compatibility fields (from original API)
    order: Optional[dict] = Field(default=None, description="Full order object (backward compatibility)")
    reply_text: Optional[str] = Field(default=None, description="Alias for draft_reply (backward compatibility)")


class AdminReviewInput(BaseModel):
    """Input for the admin review endpoint."""
    action: ReviewAction


class PendingTicket(BaseModel):
    """Ticket awaiting admin approval."""
    thread_id: str
    order_id: Optional[str] = None
    customer_name: Optional[str] = None
    issue_type: Optional[str] = None
    suggested_action: Optional[str] = None
    applied_policies: Optional[list[dict]] = None
    draft_reply: Optional[str] = None
    created_at: Optional[str] = None


class PendingTicketsResponse(BaseModel):
    """Response for GET /admin/review - list of pending tickets."""
    pending_count: int
    tickets: list[PendingTicket]
