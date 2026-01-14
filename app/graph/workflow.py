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
RouteAfterIngest = Literal["classify_issue", "resolve_order", "draft_reply", "admin_review"]
RouteAfterDraft = Literal["finalize", "__end__"]


def route_after_ingest(state: GraphState) -> RouteAfterIngest:
    """
    Route based on ingest analysis for multi-turn conversation support.
    
    Routing logic:
    - ADMIN_RESUME → admin_review (admin has made decision, process it)
    - FULL / RECLASSIFY → classify_issue (continue normal classification flow)
    - RESOLVE → resolve_order (skip classification, go to resolution)
    - DRAFT → draft_reply (skip to draft, use existing context)
    
    Args:
        state: Current graph state.
        
    Returns:
        Next node name.
    """
    route_path = state.get("route_path", RoutePath.FULL)
    
    if route_path == RoutePath.ADMIN_RESUME:
        return "admin_review"
    elif route_path in (RoutePath.FULL, RoutePath.RECLASSIFY):
        return "classify_issue"
    elif route_path == RoutePath.RESOLVE:
        return "resolve_order"
    else:  # DRAFT
        return "draft_reply"


def route_after_draft(state: GraphState) -> RouteAfterDraft:
    """
    Route after draft based on the scenario and admin_approved state.
    
    For REPLY scenario:
    - admin_approved is None -> END (pending, wait for admin)
    - admin_approved is not None -> finalize (after admin_review)
    
    All other scenarios end the run and await the next user message.
    
    Args:
        state: Current graph state.
        
    Returns:
        Next node name or END.
    """
    scenario = state.get("draft_scenario")
    admin_approved = state.get("admin_approved")
    
    if scenario == DraftScenario.REPLY:
        # Check if admin has made a decision
        if admin_approved is not None:
            return "finalize"
        else:
            # First run - end and wait for admin decision
            return END
    else:
        # Other scenarios don't need admin approval - return to user
        return END


def create_graph() -> StateGraph:
    """
    Create and return the Ticket Triage graph builder.
    
    Conditional Flow (No Interrupt):
    ```
    START -> ingest -> route_after_ingest
      |-> classify_issue (FULL/RECLASSIFY) -> resolve_order -> draft_reply
      |-> resolve_order (RESOLVE) -> draft_reply
      |-> draft_reply (DRAFT - continuation)
      |-> admin_review (ADMIN_RESUME) -> draft_reply
    
    resolve_order handles:
      - Order ID present -> fetch -> found/not found
      - Email present -> search -> 0/1/N results
      - Neither -> need_identifier
      - For REPLY: sets suggested_action, admin_approved=None
    
    draft_reply (first run, admin_approved=None):
      - Generates "ticket raised" acknowledgment
      - route_after_draft -> END (pending)
    
    admin_review (via ADMIN_RESUME route):
      - Sets admin_approved=True/False based on review_status
      - -> draft_reply
    
    draft_reply (second run, admin_approved=True/False):
      - Generates final message (approved action or rejection)
      - route_after_draft -> finalize -> END
    ```
    
    Returns:
        StateGraph builder ready for compilation.
    """
    builder = StateGraph(GraphState)
    
    # Add nodes (6 nodes - no prepare_action)
    builder.add_node("ingest", ingest)
    builder.add_node("classify_issue", classify_issue)
    builder.add_node("resolve_order", resolve_order)
    builder.add_node("draft_reply", draft_reply)
    builder.add_node("admin_review", admin_review)
    builder.add_node("finalize", finalize)
    
    # Entry point
    builder.add_edge(START, "ingest")
    
    # After ingest -> route based on context (multi-turn support + admin resume)
    builder.add_conditional_edges(
        "ingest",
        route_after_ingest,
        {
            "classify_issue": "classify_issue",
            "resolve_order": "resolve_order",
            "draft_reply": "draft_reply",
            "admin_review": "admin_review",
        }
    )
    
    # Linear flow for nodes that always proceed to next
    builder.add_edge("classify_issue", "resolve_order")
    builder.add_edge("resolve_order", "draft_reply")
    
    # After draft -> route based on scenario and admin_approved
    builder.add_conditional_edges(
        "draft_reply",
        route_after_draft,
        {
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
