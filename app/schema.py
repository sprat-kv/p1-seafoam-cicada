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
    REQUEST_CHANGES = "request_changes"


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
    issue_type: Optional[str] = None
    draft_reply: Optional[str] = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    messages: list[dict] = Field(default_factory=list)


class AdminReviewInput(BaseModel):
    """Input for the admin review endpoint."""
    action: ReviewAction
