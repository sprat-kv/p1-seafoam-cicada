"""
Node implementations for the Ticket Triage orchestrator.

Each node is a function that takes the current state and returns
a partial state update.
"""

from typing import Any

from app.graph.state import GraphState
from app.schema import ReviewStatus
from app.graph.tools import fetch_order


def ingest(state: GraphState) -> dict[str, Any]:
    """
    Ingest node: Parse user input and extract order_id if present.
    
    Responsibilities:
    - Extract order_id from ticket_text using regex or LLM.
    - Set initial state values.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with extracted information.
    """
    import re
    from langchain_core.messages import HumanMessage
    
    ticket_text = state.get("ticket_text", "")
    order_id = state.get("order_id")
    
    # If order_id not provided, try to extract from ticket_text
    if not order_id and ticket_text:
        # Look for pattern like ORD1001, ORD1234, etc.
        match = re.search(r'\b(ORD\d{4})\b', ticket_text, re.IGNORECASE)
        if match:
            order_id = match.group(1).upper()
    
    # Add user message to conversation history
    messages = [HumanMessage(content=ticket_text)]
    
    return {
        "order_id": order_id,
        "messages": messages,
        "sender": "ingest"
    }


def classify_issue(state: GraphState) -> dict[str, Any]:
    """
    Classify node: Determine the issue type from the ticket.
    
    Responsibilities:
    - Analyze ticket_text to determine issue category.
    - Use keyword matching or LLM classification.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with issue_type.
    """
    import json
    import os
    
    ticket_text = state.get("ticket_text", "").lower()
    
    # Load issue classification rules
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    issues_path = os.path.join(root, "mock_data", "issues.json")
    
    with open(issues_path, "r", encoding="utf-8") as f:
        issues = json.load(f)
    
    # Match keywords to classify issue
    issue_type = "unknown"
    for rule in issues:
        if rule["keyword"] in ticket_text:
            issue_type = rule["issue_type"]
            break
    
    return {
        "issue_type": issue_type,
        "sender": "classify_issue"
    }


def fetch_order_node(state: GraphState) -> dict[str, Any]:
    """
    Fetch Order node: Retrieve order details using the fetch_order tool.
    
    This is a wrapper around the fetch_order tool that integrates it
    into the graph flow without requiring AI message tool calls.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with order_details.
    """
    order_id = state.get("order_id")
    
    if not order_id:
        return {
            "order_details": None,
            "sender": "fetch_order_node"
        }
    
    # Call the tool directly
    order_details = fetch_order.invoke({"order_id": order_id})
    
    return {
        "order_details": order_details,
        "sender": "fetch_order_node"
    }


def draft_reply(state: GraphState) -> dict[str, Any]:
    """
    Draft Reply node: Generate a proposed response for the customer.
    
    Responsibilities:
    - Use issue_type, order_details, and templates to draft a response.
    - Consider admin_feedback if this is a retry.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with draft_reply and recommendation.
    """
    import json
    import os
    from langchain_core.messages import AIMessage
    
    issue_type = state.get("issue_type", "unknown")
    order_details = state.get("order_details")
    admin_feedback = state.get("admin_feedback")
    
    # Load reply templates
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    replies_path = os.path.join(root, "mock_data", "replies.json")
    
    with open(replies_path, "r", encoding="utf-8") as f:
        replies = json.load(f)
    
    # Find template for issue type
    template = None
    for reply_rule in replies:
        if reply_rule["issue_type"] == issue_type:
            template = reply_rule["template"]
            break
    
    # Fallback template if no match
    if not template:
        template = "Hi {{customer_name}}, we are reviewing order {{order_id}}. We will get back to you shortly."
    
    # Fill in template variables
    if order_details:
        draft = template.replace("{{customer_name}}", order_details.get("customer_name", "Customer"))
        draft = draft.replace("{{order_id}}", order_details.get("order_id", ""))
    else:
        draft = template.replace("{{customer_name}}", "Customer")
        draft = draft.replace("{{order_id}}", state.get("order_id", ""))
    
    # If admin provided feedback, append it to the draft
    if admin_feedback:
        draft = f"{draft}\n\n[Admin Note: {admin_feedback}]"
    
    # Create evidence summary
    evidence = f"Order ID: {state.get('order_id', 'N/A')}, Issue Type: {issue_type}"
    if order_details:
        evidence += f", Status: {order_details.get('status', 'N/A')}"
    
    # Create recommendation
    recommendation = f"Recommend {issue_type} resolution for order {state.get('order_id', 'N/A')}"
    
    # Add draft as assistant message
    draft_message = AIMessage(content=draft)
    
    return {
        "draft_reply": draft,
        "evidence": evidence,
        "recommendation": recommendation,
        "messages": [draft_message],
        "review_status": ReviewStatus.PENDING,
        "sender": "draft_reply"
    }


def admin_review(state: GraphState) -> dict[str, Any]:
    """
    Admin Review node: Process the Admin's review decision.
    
    Responsibilities:
    - This node is reached after the graph resumes from interrupt.
    - The review_status and admin_feedback are set externally before resuming.
    - This node just marks that review has been processed.
    
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


def final_response(state: GraphState) -> dict[str, Any]:
    """
    Final Response node: Finalize and record the approved response.
    
    Responsibilities:
    - Add the final response to messages.
    - Mark the triage as complete.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with final message added.
    """
    from langchain_core.messages import AIMessage
    
    draft_reply = state.get("draft_reply", "")
    
    # Create final message
    final_message = AIMessage(
        content=f"[APPROVED] {draft_reply}",
        name="assistant"
    )
    
    return {
        "messages": [final_message],
        "sender": "final_response"
    }
