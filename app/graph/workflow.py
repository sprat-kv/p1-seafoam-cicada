"""
LangGraph workflow definition for the Ticket Triage orchestrator.
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import GraphState
from app.graph.nodes import (
    ingest,
    classify_issue,
    fetch_order_node,
    draft_reply,
    admin_review,
    final_response,
)


def route_after_ingest(state: GraphState) -> Literal["classify_issue", "__end__"]:
    """
    Route after ingestion based on whether order_id was extracted.
    
    Args:
        state: Current graph state.
        
    Returns:
        Next node name or END.
    """
    order_id = state.get("order_id")
    
    if order_id:
        return "classify_issue"
    else:
        # No order_id found - need user to provide it
        return END


def route_after_admin_review(state: GraphState) -> Literal["final_response", "classify_issue", "draft_reply"]:
    """
    Route after admin review based on the review decision.
    
    Args:
        state: Current graph state.
        
    Returns:
        Next node name based on review_status.
    """
    from app.schema import ReviewStatus
    
    review_status = state.get("review_status", ReviewStatus.PENDING)
    
    if review_status == ReviewStatus.APPROVED:
        # Approved - send the response
        return "final_response"
    elif review_status == ReviewStatus.REJECTED:
        # Rejected - restart from classification
        return "classify_issue"
    elif review_status == ReviewStatus.REQUEST_CHANGES:
        # Request changes - redraft the reply
        return "draft_reply"
    else:
        # Default to final_response (shouldn't happen)
        return "final_response"


def create_graph() -> StateGraph:
    """
    Create and return the Ticket Triage graph builder.
    
    Graph Flow:
    1. START -> ingest
    2. ingest -> classify_issue (if order_id exists) or END (ask for ID)
    3. classify_issue -> fetch_order (ToolNode)
    4. fetch_order -> draft_reply
    5. draft_reply -> admin_review (INTERRUPT HERE in Stage 3)
    6. admin_review -> final_response (if APPROVED)
                    -> classify_issue (if REJECTED - full retry)
                    -> draft_reply (if REQUEST_CHANGES - redraft)
    7. final_response -> END
    
    Returns:
        StateGraph builder ready for compilation.
    """
    # Initialize the graph builder
    builder = StateGraph(GraphState)
    
    # Add nodes
    builder.add_node("ingest", ingest)
    builder.add_node("classify_issue", classify_issue)
    builder.add_node("fetch_order", fetch_order_node)
    builder.add_node("draft_reply", draft_reply)
    builder.add_node("admin_review", admin_review)
    builder.add_node("final_response", final_response)
    
    # Define edges
    builder.add_edge(START, "ingest")
    
    # Conditional routing after ingest
    builder.add_conditional_edges(
        "ingest",
        route_after_ingest,
        {
            "classify_issue": "classify_issue",
            "__end__": END
        }
    )
    
    # Linear flow through classification, tool calling, and drafting
    builder.add_edge("classify_issue", "fetch_order")
    builder.add_edge("fetch_order", "draft_reply")
    
    # Draft goes to admin_review (will interrupt before admin_review)
    builder.add_edge("draft_reply", "admin_review")
    
    # Conditional routing after admin review based on decision
    builder.add_conditional_edges(
        "admin_review",
        route_after_admin_review,
        {
            "final_response": "final_response",
            "classify_issue": "classify_issue",
            "draft_reply": "draft_reply"
        }
    )
    
    builder.add_edge("final_response", END)
    
    return builder


def compile_graph(checkpointer=None, interrupt_before=None):
    """
    Compile the graph with optional checkpointer and interrupts.
    
    Args:
        checkpointer: Optional checkpointer for persistence (e.g., MemorySaver()).
        interrupt_before: List of node names to interrupt before (default: ["admin_review"]).
        
    Returns:
        Compiled graph.
    """
    builder = create_graph()
    
    # Default interrupt before admin_review for HITL
    if interrupt_before is None:
        interrupt_before = []
    
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
    )


# Default graph instance (without checkpointer for basic testing)
# For HITL workflows, use compile_graph() with MemorySaver() and interrupt_before=["admin_review"]
graph = compile_graph()
