"""
Graph State definition for the Ticket Triage orchestrator.
"""

from typing import Annotated, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages

from app.schema import ReviewStatus, DraftScenario, RoutePath


class GraphState(TypedDict):
    """
    State schema for the Ticket Triage LangGraph.
    
    Attributes:
        messages: Conversation history (User, Assistant, Admin).
        ticket_text: The current ticket/message text from the user.
        order_id: Extracted or provided order ID.
        email: Extracted customer email from ticket_text.
        issue_type: Classified issue category.
        order_details: Fetched order information (dict representation).
        candidate_orders: List of orders found from email search.
        evidence: Supporting information gathered during triage.
        recommendation: The action recommendation for the ticket.
        draft_reply: The Assistant's proposed response text.
        draft_scenario: The scenario type for the unified draft node.
        route_path: Routing decision from ingest for multi-turn support.
        suggested_action: Template-based action for admin to review.
        review_status: Current status of Admin review (PENDING, APPROVED, REJECTED).
        admin_feedback: Feedback from Admin (optional).
        sender: The last node that modified the state.
    """
    messages: Annotated[list, add_messages]
    ticket_text: str
    order_id: Optional[str]
    email: Optional[str]
    issue_type: Optional[str]
    order_details: Optional[dict]
    candidate_orders: Optional[list[dict]]
    evidence: Optional[str]
    recommendation: Optional[str]
    draft_reply: Optional[str]
    draft_scenario: Optional[DraftScenario]
    route_path: Optional[RoutePath]
    suggested_action: Optional[str]
    review_status: Optional[ReviewStatus]
    admin_feedback: Optional[str]
    sender: Optional[str]
