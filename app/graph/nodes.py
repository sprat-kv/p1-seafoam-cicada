"""
Node implementations for the Ticket Triage orchestrator.

Each node is a function that takes the current state and returns
a partial state update.
"""

import json
import os
import re
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from app.graph.state import GraphState
from app.schema import ReviewStatus, DraftScenario
from app.graph.tools import fetch_order, search_orders

# LLM instance - lazy initialized
_llm = None


def get_llm():
    """Get or create the LLM instance (lazy initialization)."""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    return _llm


# Path to mock data
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MOCK_DIR = os.path.join(ROOT, "mock_data")


def load_templates() -> list[dict]:
    """Load reply templates from mock data."""
    with open(os.path.join(MOCK_DIR, "replies.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_issues() -> list[dict]:
    """Load issue classification rules from mock data."""
    with open(os.path.join(MOCK_DIR, "issues.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def ingest(state: GraphState) -> dict[str, Any]:
    """
    Ingest node: Parse user input and extract identifiers.
    
    Responsibilities:
    - Extract order_id from ticket_text using regex (ORD\\d+)
    - Extract email from ticket_text using regex
    - Add user message to conversation history
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with extracted information.
    """
    ticket_text = state.get("ticket_text", "")
    order_id = state.get("order_id")
    email = state.get("email")
    
    # Extract order_id if not provided
    if not order_id and ticket_text:
        match = re.search(r'\b(ORD\d+)\b', ticket_text, re.IGNORECASE)
        if match:
            order_id = match.group(1).upper()
    
    # Extract email if not provided
    if not email and ticket_text:
        email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', ticket_text, re.IGNORECASE)
        if email_match:
            email = email_match.group(0).lower()
    
    # Add user message to conversation history
    messages = [HumanMessage(content=ticket_text)]
    
    return {
        "order_id": order_id,
        "email": email,
        "messages": messages,
        "sender": "ingest"
    }


def classify_issue(state: GraphState) -> dict[str, Any]:
    """
    Classify node: Determine the issue type from the ticket using priority-based matching.
    
    Classification logic:
    - Find all keywords contained in ticket_text (case-insensitive)
    - Choose match with lowest priority value
    - Tie-breaker: longer keyword wins (more specific)
    - If no match: issue_type = "unknown"
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with issue_type, evidence, recommendation.
    """
    ticket_text = state.get("ticket_text", "").lower()
    issues = load_issues()
    
    # Find all matching keywords
    matches = []
    for rule in issues:
        keyword = rule["keyword"].lower()
        if keyword in ticket_text:
            matches.append({
                "keyword": keyword,
                "issue_type": rule["issue_type"],
                "priority": rule.get("priority", 999)
            })
    
    # Determine issue type
    if matches:
        # Sort by priority (ascending), then by keyword length (descending for tie-breaker)
        best_match = min(matches, key=lambda x: (x["priority"], -len(x["keyword"])))
        issue_type = best_match["issue_type"]
        evidence = f"Matched keyword: '{best_match['keyword']}' (priority: {best_match['priority']})"
    else:
        issue_type = "unknown"
        evidence = "No matching keywords found"
    
    recommendation = f"Recommend {issue_type} resolution"
    
    return {
        "issue_type": issue_type,
        "evidence": evidence,
        "recommendation": recommendation,
        "sender": "classify_issue"
    }


def resolve_order(state: GraphState) -> dict[str, Any]:
    """
    Unified order resolution node.
    
    Handles all order lookup scenarios in a single node:
    
    1. If order_id is present:
       - Fetch order by ID
       - If found: scenario=REPLY
       - If not found: scenario=ORDER_NOT_FOUND
    
    2. Else if email is present:
       - Search orders by email
       - 0 results: scenario=NO_ORDERS_FOUND
       - 1 result: auto-select, scenario=REPLY
       - N results: scenario=CONFIRM_ORDER
    
    3. Else (no identifier):
       - scenario=NEED_IDENTIFIER
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with order resolution results.
    """
    order_id = state.get("order_id")
    email = state.get("email")
    
    # Path 1: Order ID is present - fetch by ID
    if order_id:
        order_details = fetch_order.invoke({"order_id": order_id})
        
        if order_details:
            return {
                "order_details": order_details,
                "draft_scenario": DraftScenario.REPLY,
                "sender": "resolve_order"
            }
        else:
            return {
                "order_details": None,
                "draft_scenario": DraftScenario.ORDER_NOT_FOUND,
                "sender": "resolve_order"
            }
    
    # Path 2: Email is present - search by email
    if email:
        candidates = search_orders.invoke({"email": email})
        
        if len(candidates) == 0:
            # No orders found for this email
            return {
                "candidate_orders": candidates,
                "draft_scenario": DraftScenario.NO_ORDERS_FOUND,
                "sender": "resolve_order"
            }
        elif len(candidates) == 1:
            # Exactly one order - auto-select
            order = candidates[0]
            return {
                "order_id": order["order_id"],
                "order_details": order,
                "candidate_orders": candidates,
                "draft_scenario": DraftScenario.REPLY,
                "sender": "resolve_order"
            }
        else:
            # Multiple orders - ask user to pick
            return {
                "candidate_orders": candidates,
                "draft_scenario": DraftScenario.CONFIRM_ORDER,
                "sender": "resolve_order"
            }
    
    # Path 3: No identifier provided
    return {
        "draft_scenario": DraftScenario.NEED_IDENTIFIER,
        "sender": "resolve_order"
    }


def draft_reply(state: GraphState) -> dict[str, Any]:
    """
    Unified LLM-backed draft node.
    
    Generates contextually appropriate responses based on the draft_scenario.
    Uses templates from replies.json as guidance for tone and structure.
    
    Scenarios handled:
    - REPLY: Normal issue response using template
    - NEED_IDENTIFIER: Ask for order_id or email
    - ORDER_NOT_FOUND: Order ID invalid, ask for correct info
    - NO_ORDERS_FOUND: Email has no orders
    - CONFIRM_ORDER: Multiple orders, list options for user to pick
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with draft_reply and review_status.
    """
    scenario = state.get("draft_scenario", DraftScenario.REPLY)
    issue_type = state.get("issue_type", "unknown")
    order_details = state.get("order_details")
    candidate_orders = state.get("candidate_orders", [])
    ticket_text = state.get("ticket_text", "")
    order_id = state.get("order_id")
    email = state.get("email")
    admin_feedback = state.get("admin_feedback")
    
    templates = load_templates()
    
    # Build templates string for context
    templates_str = "\n".join([
        f"- {t['issue_type']}: {t['template']}" for t in templates
    ])
    
    # Build candidate orders string if applicable
    candidates_str = ""
    if candidate_orders:
        candidates_str = "\n".join([
            f"- {o['order_id']}: {o['items'][0]['name'] if o.get('items') else 'N/A'} ({o.get('status', 'N/A')})"
            for o in candidate_orders
        ])
    
    # Build context for LLM
    system_prompt = f"""You are a customer support assistant for an e-commerce company. Generate a helpful, professional response based on the scenario.

SCENARIO: {scenario.value if scenario else 'reply'}

Available templates (use as structure/tone guidance):
{templates_str}

Respond appropriately based on scenario:
- reply: Use the template for the issue_type, fill in customer_name and order_id placeholders
- need_identifier: Politely ask the customer to provide their order ID (format: ORD followed by numbers) or the email address associated with their order
- order_not_found: Explain that we couldn't find an order with that ID, ask them to verify and provide the correct order ID or email
- no_orders_found: Explain that we couldn't find any orders for that email address, ask them to verify and provide a different email or order ID
- confirm_order: List the candidate orders and ask the customer to specify which order they're inquiring about

Keep responses concise, friendly, and professional. Do not include internal notes or scenario labels in the response."""

    # Build user message with context
    context_parts = [f"Customer message: {ticket_text}"]
    context_parts.append(f"Issue type: {issue_type}")
    
    if order_id:
        context_parts.append(f"Order ID: {order_id}")
    if email:
        context_parts.append(f"Email: {email}")
    if order_details:
        customer_name = order_details.get("customer_name", "Customer")
        context_parts.append(f"Customer name: {customer_name}")
        context_parts.append(f"Order status: {order_details.get('status', 'N/A')}")
    if candidates_str:
        context_parts.append(f"Candidate orders:\n{candidates_str}")
    if admin_feedback:
        context_parts.append(f"Admin feedback for revision: {admin_feedback}")
    
    user_message = "\n".join(context_parts)
    
    # Invoke LLM (lazy initialization)
    response = get_llm().invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ])
    
    draft = response.content
    
    # Create evidence summary
    evidence = f"Scenario: {scenario.value if scenario else 'reply'}, Issue Type: {issue_type}"
    if order_id:
        evidence += f", Order ID: {order_id}"
    if order_details:
        evidence += f", Status: {order_details.get('status', 'N/A')}"
    
    # Create recommendation
    if scenario == DraftScenario.REPLY:
        recommendation = f"Recommend {issue_type} resolution for order {order_id or 'N/A'}"
    else:
        recommendation = f"Awaiting additional information ({scenario.value if scenario else 'unknown'})"
    
    # Add draft as assistant message
    draft_message = AIMessage(content=draft)
    
    # Only set review_status to PENDING for REPLY scenario
    review_status = ReviewStatus.PENDING if scenario == DraftScenario.REPLY else None
    
    return {
        "draft_reply": draft,
        "evidence": evidence,
        "recommendation": recommendation,
        "messages": [draft_message],
        "review_status": review_status,
        "sender": "draft_reply"
    }


def admin_review(state: GraphState) -> dict[str, Any]:
    """
    Admin Review node: Process the Admin's review decision.
    
    This node is reached after the graph resumes from interrupt.
    The review_status and admin_feedback are set externally before resuming.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update based on admin decision.
    """
    review_status = state.get("review_status", ReviewStatus.PENDING)
    
    # Log the review decision
    print(f"[Admin Review] Status: {review_status}")
    if state.get("admin_feedback"):
        print(f"[Admin Review] Feedback: {state.get('admin_feedback')}")
    
    return {"sender": "admin_review"}


def finalize(state: GraphState) -> dict[str, Any]:
    """
    Finalize node: Record the approved response and mark as complete.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with final message added.
    """
    draft_reply = state.get("draft_reply", "")
    review_status = state.get("review_status", ReviewStatus.APPROVED)
    
    # Create final message
    final_message = AIMessage(
        content=f"[FINAL] {draft_reply}",
        name="assistant"
    )
    
    return {
        "messages": [final_message],
        "review_status": ReviewStatus.APPROVED,
        "sender": "finalize"
    }
