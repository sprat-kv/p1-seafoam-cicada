"""
LangGraph workflow definition for the Ticket Triage orchestrator.

This workflow implements a deterministic routing system with:
- Python-driven routing for all control flow decisions
- Single unified order resolution node
- Single unified LLM-backed draft node for all response scenarios
- HITL (Human-in-the-Loop) admin review for reply scenarios
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import GraphState
from app.schema import ReviewStatus, DraftScenario, RoutePath
from app.graph.nodes import (
    ingest,
    classify_issue,
    resolve_order,
    prepare_action,
    draft_reply,
    admin_review,
    finalize,
)


# Type aliases for routing return types
RouteAfterIngest = Literal["classify_issue", "resolve_order", "draft_reply"]
RouteAfterDraft = Literal["admin_review", "finalize", "__end__"]
RouteAfterAdminReview = Literal["draft_reply"]


def route_after_ingest(state: GraphState) -> RouteAfterIngest:
    """
    Route based on ingest analysis for multi-turn conversation support.
    
    Routing logic:
    - FULL / RECLASSIFY → classify_issue (continue normal classification flow)
    - RESOLVE → resolve_order (skip classification, go to resolution)
    - DRAFT → draft_reply (skip to draft, use existing context)
    
    Args:
        state: Current graph state.
        
    Returns:
        Next node name.
    """
    route_path = state.get("route_path", RoutePath.FULL)
    
    if route_path in (RoutePath.FULL, RoutePath.RECLASSIFY):
        return "classify_issue"
    elif route_path == RoutePath.RESOLVE:
        return "resolve_order"
    else:  # DRAFT
        return "draft_reply"


def route_after_draft(state: GraphState) -> RouteAfterDraft:
    """
    Route after draft based on the scenario and admin_approved state.
    
    For REPLY scenario:
    - admin_approved is None -> admin_review (HITL interrupt, first run)
    - admin_approved is not None -> finalize (second run, after admin_review)
    
    Uses admin_approved (set by admin_review node) instead of review_status
    (set by API) to avoid routing changes when API updates state.
    
    All other scenarios end the run and await the next user message.
    
    Args:
        state: Current graph state.
        
    Returns:
        Next node name or END.
    """
    scenario = state.get("draft_scenario")
    admin_approved = state.get("admin_approved")
    
    if scenario == DraftScenario.REPLY:
        # Check if already reviewed using admin_approved (set by admin_review node)
        # admin_approved=None means first run (pending), not None means second run
        if admin_approved is not None:
            return "finalize"
        else:
            # First run - go to admin_review for HITL
            return "admin_review"
    else:
        # Other scenarios don't need admin approval - return to user
        return END


def route_after_admin_review(state: GraphState) -> RouteAfterAdminReview:
    """
    Route after admin review.
    
    Always routes to draft_reply to generate the appropriate response
    based on admin_approved flag (set by admin_review node):
    - admin_approved=True -> draft_reply generates approved action message
    - admin_approved=False -> draft_reply generates rejection message
    - admin_approved=None (REQUEST_CHANGES) -> draft_reply re-drafts with feedback
    
    Args:
        state: Current graph state.
        
    Returns:
        Next node name (always draft_reply).
    """
    return "draft_reply"


def create_graph() -> StateGraph:
    """
    Create and return the Ticket Triage graph builder.
    
    Two-Stage Response Flow:
    ```
    START -> ingest -> route_after_ingest
      |-> classify_issue (FULL/RECLASSIFY) -> resolve_order -> prepare_action -> draft_reply
      |-> resolve_order (RESOLVE) -> prepare_action -> draft_reply
      |-> draft_reply (DRAFT - continuation)
    
    resolve_order handles internally:
      - Order ID present -> fetch -> found/not found
      - Email present -> search -> 0/1/N results
      - Neither -> need_identifier
    
    prepare_action:
      - Collects suggested_action from template
      - Sets admin_approved=None (pending)
    
    draft_reply (first run, admin_approved=None):
      - Generates "ticket raised" acknowledgment
      - route_after_draft -> admin_review (HITL interrupt)
    
    admin_review:
      - Sets admin_approved=True/False based on review_status
      - route_after_admin_review -> draft_reply
    
    draft_reply (second run, admin_approved=True/False):
      - Generates final message (approved action or rejection)
      - route_after_draft -> finalize -> END
    ```
    
    Returns:
        StateGraph builder ready for compilation.
    """
    builder = StateGraph(GraphState)
    
    # Add nodes (7 nodes)
    builder.add_node("ingest", ingest)
    builder.add_node("classify_issue", classify_issue)
    builder.add_node("resolve_order", resolve_order)
    builder.add_node("prepare_action", prepare_action)
    builder.add_node("draft_reply", draft_reply)
    builder.add_node("admin_review", admin_review)
    builder.add_node("finalize", finalize)
    
    # Entry point
    builder.add_edge(START, "ingest")
    
    # After ingest -> route based on context (multi-turn support)
    builder.add_conditional_edges(
        "ingest",
        route_after_ingest,
        {
            "classify_issue": "classify_issue",
            "resolve_order": "resolve_order",
            "draft_reply": "draft_reply",
        }
    )
    
    # Linear flow for nodes that always proceed to next
    builder.add_edge("classify_issue", "resolve_order")
    builder.add_edge("resolve_order", "prepare_action")
    builder.add_edge("prepare_action", "draft_reply")
    
    # After draft -> route based on scenario and review status
    builder.add_conditional_edges(
        "draft_reply",
        route_after_draft,
        {
            "admin_review": "admin_review",
            "finalize": "finalize",
            "__end__": END,
        }
    )
    
    # After admin review -> always go to draft_reply for final message
    builder.add_edge("admin_review", "draft_reply")
    
    # Final node leads to END
    builder.add_edge("finalize", END)
    
    return builder


def compile_graph(checkpointer=None, interrupt_before=None):
    """
    Compile the graph with optional checkpointer and interrupts.
    
    Args:
        checkpointer: Optional checkpointer for persistence (e.g., MemorySaver()).
        interrupt_before: List of node names to interrupt before.
                         Default: ["admin_review"] for HITL.
        
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
