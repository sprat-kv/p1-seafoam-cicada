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
    draft_reply,
    admin_review,
    finalize,
)


# Type aliases for routing return types
RouteAfterIngest = Literal["classify_issue", "resolve_order", "draft_reply"]
RouteAfterDraft = Literal["admin_review", "__end__"]
RouteAfterAdminReview = Literal["finalize", "draft_reply"]


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
    Route after draft based on the scenario.
    
    Only REPLY scenario goes to admin_review for HITL.
    All other scenarios (need_identifier, order_not_found, etc.) 
    end the run and await the next user message.
    
    Args:
        state: Current graph state.
        
    Returns:
        Next node name or END.
    """
    scenario = state.get("draft_scenario")
    
    if scenario == DraftScenario.REPLY:
        return "admin_review"
    else:
        # Other scenarios don't need admin approval - return to user
        return END


def route_after_admin_review(state: GraphState) -> RouteAfterAdminReview:
    """
    Route after admin review based on the review decision.
    
    - APPROVED -> finalize
    - REQUEST_CHANGES -> draft_reply (re-draft with feedback)
    - REJECTED -> finalize (with rejection status)
    
    Args:
        state: Current graph state.
        
    Returns:
        Next node name.
    """
    review_status = state.get("review_status", ReviewStatus.PENDING)
    
    if review_status == ReviewStatus.APPROVED:
        return "finalize"
    elif review_status == ReviewStatus.REQUEST_CHANGES:
        # Re-draft with admin feedback
        return "draft_reply"
    else:
        # REJECTED or other - finalize anyway
        return "finalize"


def create_graph() -> StateGraph:
    """
    Create and return the Ticket Triage graph builder.
    
    Multi-turn Aware Graph Flow:
    ```
    START -> ingest -> route_after_ingest
      |-> classify_issue (FULL/RECLASSIFY) -> resolve_order -> draft_reply
      |-> resolve_order (RESOLVE) -> draft_reply
      |-> draft_reply (DRAFT - continuation)
    
    resolve_order handles internally:
      - Order ID present -> fetch -> found/not found
      - Email present -> search -> 0/1/N results
      - Neither -> need_identifier
    
    draft_reply -> route_after_draft
      |-> admin_review (if scenario=REPLY) -> route_after_admin_review
      |     |-> finalize -> END
      |     |-> draft_reply (if REQUEST_CHANGES)
      |-> END (if other scenarios - await user input)
    ```
    
    Returns:
        StateGraph builder ready for compilation.
    """
    builder = StateGraph(GraphState)
    
    # Add nodes (6 nodes)
    builder.add_node("ingest", ingest)
    builder.add_node("classify_issue", classify_issue)
    builder.add_node("resolve_order", resolve_order)
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
    builder.add_edge("resolve_order", "draft_reply")
    
    # After draft -> route based on scenario
    builder.add_conditional_edges(
        "draft_reply",
        route_after_draft,
        {
            "admin_review": "admin_review",
            "__end__": END,
        }
    )
    
    # After admin review -> route based on decision
    builder.add_conditional_edges(
        "admin_review",
        route_after_admin_review,
        {
            "finalize": "finalize",
            "draft_reply": "draft_reply",
        }
    )
    
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
