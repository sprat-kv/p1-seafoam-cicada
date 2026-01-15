"""
Node implementations for the Ticket Triage orchestrator.

Each node is a function that takes the current state and returns
a partial state update.
"""

import json
import os
import re
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.graph.state import GraphState
from app.schema import ReviewStatus, DraftScenario, RoutePath
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


def check_issue_keywords(text: str) -> bool:
    """
    Check if text contains any issue keywords from issues.json.
    
    Args:
        text: Text to check for issue keywords.
        
    Returns:
        True if any issue keyword is found, False otherwise.
    """
    if not text:
        return False
    issues = load_issues()
    text_lower = text.lower()
    return any(rule["keyword"].lower() in text_lower for rule in issues)


def extract_order_id(text: str) -> str | None:
    """Extract order ID from text using regex."""
    if not text:
        return None
    match = re.search(r'\b(ORD\d+)\b', text, re.IGNORECASE)
    return match.group(1).upper() if match else None


def extract_email(text: str) -> str | None:
    """Extract email from text using regex."""
    if not text:
        return None
    match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text, re.IGNORECASE)
    return match.group(0).lower() if match else None


def ingest(state: GraphState) -> dict[str, Any]:
      """
      Ingest node for multi-turn conversations.

      Routing logic:
      - No order_details yet → FULL (extract identifiers, run full pipeline)
      - Has order_details → DRAFT (follow-up, skip to draft_reply)

      Args:
          state: Current graph state.

      Returns:
          Partial state update with extracted information and route_path.
      """
      ticket_text = state.get("ticket_text", "")
      existing_order_details = state.get("order_details")

      messages = [HumanMessage(content=ticket_text)]

      if existing_order_details:
          return {
              "route_path": RoutePath.DRAFT,
              "draft_scenario": None,      # Reset so draft_reply uses LLM path
              "admin_approved": None,      # Reset to avoid APPROVED/REJECTED path
              "messages": messages,
              "sender": "ingest"
          }
      else:
          order_id = extract_order_id(ticket_text)
          email = extract_email(ticket_text)

          return {
              "order_id": order_id,
              "email": email,
              "route_path": RoutePath.FULL,
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


def prepare_action(state: GraphState) -> dict[str, Any]:
    """
    Prepare action for admin review.
    
    Collects information for admin to review:
    - Looks up suggested action from template based on issue_type
    - Sets admin_approved to None (pending)
    
    Only runs for REPLY scenario (issue identified + order found).
    Does NOT generate user message - that's draft_reply's job.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with suggested_action and admin_approved.
    """
    issue_type = state.get("issue_type", "unknown")
    order_id = state.get("order_id")
    order_details = state.get("order_details", {})
    customer_name = order_details.get("customer_name", "Customer") if order_details else "Customer"
    
    # Get suggested action from template
    templates = load_templates()
    template = next((t["template"] for t in templates if t["issue_type"] == issue_type), None)
    
    if template:
        suggested_action = template.replace("{{customer_name}}", customer_name).replace("{{order_id}}", order_id or "N/A")
    else:
        suggested_action = f"Process {issue_type} request for order {order_id or 'N/A'}"
    
    return {
        "suggested_action": suggested_action,
        "admin_approved": None,  # Pending - triggers "ticket raised" in draft_reply
        "sender": "prepare_action"
    }


def draft_reply(state: GraphState) -> dict[str, Any]:
    """
    Unified draft node that generates responses based on admin approval state.
    
    For REPLY scenario, response depends on admin_approved:
    - None (pending): Generate "ticket raised" acknowledgment (no LLM)
    - True (approved): Generate full action message using LLM
    - False (rejected): Generate rejection message (no LLM)
    
    For non-REPLY scenarios (need_identifier, etc.): Use LLM as before.
    
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
    admin_approved = state.get("admin_approved")
    suggested_action = state.get("suggested_action")
    messages = state.get("messages", [])
    
    # For REPLY scenario, handle based on admin_approved state
    if scenario == DraftScenario.REPLY:
        if admin_approved is None:
            # PENDING: Generate acknowledgment message (no LLM needed)
            issue_labels = {
                "refund_request": "refund request",
                "wrong_item": "wrong item issue",
                "missing_item": "missing item",
                "late_delivery": "delivery delay",
                "damaged_item": "damaged item report",
                "duplicate_charge": "duplicate charge",
                "defective_product": "defective product report",
            }
            issue_label = issue_labels.get(issue_type, "issue")
            customer_name = order_details.get("customer_name", "Customer") if order_details else "Customer"
            
            draft = f"Hi {customer_name}, we identified a {issue_label} for order {order_id}. Your ticket has been raised and is under review. We will update you shortly."
            
            # Create evidence and recommendation
            evidence = f"Scenario: {scenario.value}, Issue Type: {issue_type}, Order ID: {order_id}"
            if order_details:
                evidence += f", Status: {order_details.get('status', 'N/A')}"
            recommendation = f"Awaiting admin approval for {issue_type} resolution"
            
            return {
                "draft_reply": draft,
                "evidence": evidence,
                "recommendation": recommendation,
                "messages": [AIMessage(content=draft)],
                "review_status": ReviewStatus.PENDING,
                "sender": "draft_reply"
            }
        
        elif admin_approved is True:
            # APPROVED: Generate full action message using LLM
            # Use suggested_action as base and personalize with LLM
            customer_name = order_details.get("customer_name", "Customer") if order_details else "Customer"
            
            system_prompt = f"""You are a customer support assistant. Generate a professional response confirming the approved action for the customer.

The admin has APPROVED the following action:
{suggested_action}

Personalize and enhance this message while keeping the same intent. Be warm, professional, and reassuring.
Include any relevant details about next steps or timeline if appropriate."""

            user_message = f"""Customer: {customer_name}
Order ID: {order_id}
Issue Type: {issue_type}
Order Status: {order_details.get('status', 'N/A') if order_details else 'N/A'}
Admin feedback: {admin_feedback or 'None'}"""

            response = get_llm().invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])
            
            draft = response.content
            evidence = f"Scenario: {scenario.value}, Issue Type: {issue_type}, Order ID: {order_id}, Admin: APPROVED"
            recommendation = f"Approved {issue_type} resolution for order {order_id}"
            
            return {
                "draft_reply": draft,
                "evidence": evidence,
                "recommendation": recommendation,
                "messages": [AIMessage(content=draft)],
                "review_status": ReviewStatus.APPROVED,
                "sender": "draft_reply"
            }
        
        else:  # admin_approved is False
            # REJECTED: Generate rejection message (no LLM needed)
            customer_name = order_details.get("customer_name", "Customer") if order_details else "Customer"
            
            draft = f"Hi {customer_name}, we reviewed your request regarding order {order_id} and found no issues with the order at this time. We cannot proceed with the requested action. If you believe this is an error, please provide additional details or contact us with more information."
            
            evidence = f"Scenario: {scenario.value}, Issue Type: {issue_type}, Order ID: {order_id}, Admin: REJECTED"
            recommendation = f"Rejected {issue_type} request for order {order_id}"
            
            return {
                "draft_reply": draft,
                "evidence": evidence,
                "recommendation": recommendation,
                "messages": [AIMessage(content=draft)],
                "review_status": ReviewStatus.REJECTED,
                "sender": "draft_reply"
            }
    
    # For non-REPLY scenarios, use LLM as before
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
    
    # Build conversation history from last 5 messages (excluding current)
    conversation_history = ""
    if len(messages) > 1:
        recent_messages = messages[-6:-1] if len(messages) > 5 else messages[:-1]
        history_parts = []
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                role = "Customer"
            elif isinstance(msg, AIMessage):
                role = "Agent"
            else:
                role = "System"
            content = msg.content if hasattr(msg, "content") else str(msg)
            if not content.startswith("[FINAL]"):
                history_parts.append(f"{role}: {content}")
        if history_parts:
            conversation_history = "\n".join(history_parts)
    
    history_section = f"\nCONVERSATION HISTORY (for context):\n{conversation_history}\n" if conversation_history else ""
    
    system_prompt = f"""You are a customer support assistant for an e-commerce company. Generate a helpful, professional response based on the scenario and conversation context.

SCENARIO: {scenario.value if scenario else 'reply'}
{history_section}
Available templates (use as structure/tone guidance):
{templates_str}

Respond appropriately based on scenario:
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
    
    user_message = "\n".join(context_parts)
    
    response = get_llm().invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ])
    
    draft = response.content
    
    # Create evidence summary
    evidence = f"Scenario: {scenario.value if scenario else 'unknown'}, Issue Type: {issue_type}"
    if order_id:
        evidence += f", Order ID: {order_id}"
    
    recommendation = f"Awaiting additional information ({scenario.value if scenario else 'unknown'})"
    
    return {
        "draft_reply": draft,
        "evidence": evidence,
        "recommendation": recommendation,
        "messages": [AIMessage(content=draft)],
        "review_status": None,
        "sender": "draft_reply"
    }


def admin_review(state: GraphState) -> dict[str, Any]:
    """
    Admin Review node: Process the Admin's review decision.
    
    This node is reached after the graph resumes from interrupt.
    The review_status and admin_feedback are set externally before resuming.
    
    Sets admin_approved based on review_status:
    - APPROVED → True
    - REJECTED → False
    - REQUEST_CHANGES → None (triggers re-draft)
    - PENDING → None
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with admin_approved flag.
    """
    review_status = state.get("review_status", ReviewStatus.PENDING)
    
    # Set admin_approved based on review_status
    if review_status == ReviewStatus.APPROVED:
        admin_approved = True
    elif review_status == ReviewStatus.REJECTED:
        admin_approved = False
    else:
        # REQUEST_CHANGES or PENDING - keep None to trigger re-draft with feedback
        admin_approved = None
    
    return {
        "admin_approved": admin_approved,
        "sender": "admin_review"
    }


def finalize(state: GraphState) -> dict[str, Any]:
    """
    Finalize node: Record the response and mark as complete.
    
    Preserves the existing review_status (APPROVED or REJECTED) set by draft_reply.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with final message added.
    """
    draft_reply = state.get("draft_reply", "")
    
    # Create final message
    final_message = AIMessage(
        content=f"[FINAL] {draft_reply}",
        name="assistant"
    )
    
    # Preserve existing review_status (don't overwrite)
    return {
        "messages": [final_message],
        "sender": "finalize"
    }
