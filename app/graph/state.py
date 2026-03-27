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
        policy_citations: Retrieved policy snippets from RAG retrieval.
        policy_evaluation: Policy compliance summary derived from citations.
        applied_policies: Structured policy list for admin/frontend display.
        confidence_score: Decision confidence score from decision_maker (0.0-1.0).
        decision_action: Decision maker action ("approved" or "rejected").
        decision_reasoning: Decision rationale for audit/logging.
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
    policy_citations: Optional[list[dict]]
    policy_evaluation: Optional[str]
    applied_policies: Optional[list[dict]]
    confidence_score: Optional[float]
    decision_action: Optional[str]
    decision_reasoning: Optional[str]
    review_status: Optional[ReviewStatus]
    admin_feedback: Optional[str]
    sender: Optional[str]
