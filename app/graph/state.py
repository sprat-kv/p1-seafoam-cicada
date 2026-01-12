"""
Graph State definition for the Ticket Triage orchestrator.
"""

from typing import Annotated, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages

from app.schema import ReviewStatus


class GraphState(TypedDict):
    """
    State schema for the Ticket Triage LangGraph.
    
    Attributes:
        messages: Conversation history (User, Assistant, Admin).
        ticket_text: The current ticket/message text from the user.
        order_id: Extracted or provided order ID.
        issue_type: Classified issue category.
        order_details: Fetched order information (dict representation).
        evidence: Supporting information gathered during triage.
        recommendation: The action recommendation for the ticket.
        draft_reply: The Assistant's proposed response text.
        review_status: Current status of Admin review.
        admin_feedback: Feedback from Admin (for edits/rejections).
        sender: The last node that modified the state.
    """
    messages: Annotated[list, add_messages]
    ticket_text: str
    order_id: Optional[str]
    issue_type: Optional[str]
    order_details: Optional[dict]
    evidence: Optional[str]
    recommendation: Optional[str]
    draft_reply: Optional[str]
    review_status: ReviewStatus
    admin_feedback: Optional[str]
    sender: Optional[str]
