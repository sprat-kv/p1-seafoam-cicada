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
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from langchain_openai import ChatOpenAI

from app.graph.state import GraphState
from app.schema import ReviewStatus, DraftScenario, RoutePath
from app.graph.tools import fetch_order, search_orders

# LLM instance - lazy initialized
_llm = None


def _coerce_draft_scenario(value: Any) -> DraftScenario:
    """Normalize stored scenario values to DraftScenario enum."""
    if isinstance(value, DraftScenario):
        return value
    if isinstance(value, str):
        try:
            return DraftScenario(value)
        except ValueError:
            return DraftScenario.REPLY
    return DraftScenario.REPLY


def _coerce_review_status(value: Any) -> ReviewStatus | None:
    """Normalize stored review status values to ReviewStatus enum."""
    if isinstance(value, ReviewStatus):
        return value
    if isinstance(value, str):
        try:
            return ReviewStatus(value)
        except ValueError:
            return None
    return None


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

      Smart routing logic - fills missing states only once:
      - FULL: Both issue_type AND order_details missing → Run classify + resolve
      - RECLASSIFY: Only issue_type missing (or "unknown") → Run classify only
      - RESOLVE: Only order_details missing → Run resolve only
      - DRAFT: Both states filled → Skip to draft (no re-detection)

      Args:
          state: Current graph state.

      Returns:
          Partial state update with extracted information and route_path.
      """
      ticket_text = state.get("ticket_text", "")
      existing_issue_type = state.get("issue_type")
      existing_order_details = state.get("order_details")

      messages = [HumanMessage(content=ticket_text)]

      # Determine what's missing
      needs_order = existing_order_details is None
      needs_issue = existing_issue_type is None or existing_issue_type == "unknown"

      # Extract new info from current message only if needed
      update = {"messages": messages, "sender": "ingest"}

      if needs_order:
          order_id = extract_order_id(ticket_text)
          email = extract_email(ticket_text)
          if order_id:
              update["order_id"] = order_id
          if email:
              update["email"] = email

      # Route decision based on what's missing
      if needs_order and needs_issue:
          # Both missing → Full pipeline (classify + resolve)
          update["route_path"] = RoutePath.FULL
      elif needs_order:
          # Only order missing → Skip classification, go to resolve
          update["route_path"] = RoutePath.RESOLVE
      elif needs_issue:
          # Only issue missing → Skip resolve, go to classification
          update["route_path"] = RoutePath.RECLASSIFY
      else:
          # Both filled → Skip to draft (follow-up question)
          update["route_path"] = RoutePath.DRAFT

      return update


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
    - Sets review_status to PENDING (awaiting admin approval)
    
    Only runs for REPLY scenario (issue identified + order found).
    Does NOT generate user message - that's draft_reply's job.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with suggested_action and review_status.
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
        "review_status": ReviewStatus.PENDING,  # Set to PENDING - awaiting admin approval
        "sender": "prepare_action"
    }


def generate_draft_with_llm(
    scenario: DraftScenario,
    phase: str,
    state: GraphState,
    templates: list[dict]
) -> str:
    """
    Generate customer response using LLM with conversation context and guidelines.
    
    Args:
        scenario: Current draft scenario (REPLY, NEED_IDENTIFIER, etc.)
        phase: Specific phase for REPLY scenario (unknown/pending/approved/rejected)
        state: Current graph state with all context
        templates: Reply templates to use as few-shot examples
        
    Returns:
        Generated response text
    """
    # Extract state information
    issue_type = state.get("issue_type", "unknown")
    order_details = state.get("order_details")
    order_id = state.get("order_id")
    ticket_text = state.get("ticket_text", "")
    messages = state.get("messages", [])
    candidate_orders = state.get("candidate_orders", [])
    
    customer_name = order_details.get("customer_name", "Customer") if order_details else "Customer"
    
    # Get last 5 message exchanges using LangChain's trim_messages utility
    history_section = ""
    if messages and len(messages) > 1:
        # Keep last 10 messages (5 exchanges: customer + agent pairs), excluding current
        recent_messages = trim_messages(
            messages[:-1],  # Exclude current message
            strategy="last",
            token_counter=count_tokens_approximately,  # Required: token counting function
            max_tokens=2000,  # Reasonable limit for conversation context
            start_on="human",
            end_on=("human", "ai"),
        )
        
        # Format for prompt
        history_parts = []
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                role = "Customer"
            elif isinstance(msg, AIMessage):
                role = "Agent"
            else:
                continue
            
            content = msg.content if hasattr(msg, "content") else str(msg)
            # Skip final messages and system messages
            if not content.startswith("[FINAL]") and not content.startswith("[SYSTEM]"):
                history_parts.append(f"{role}: {content}")
        
        if history_parts:
            history_section = f"\n\n## Recent Conversation\n" + "\n".join(history_parts) + "\n"
    
    # Build few-shot examples from templates
    few_shot_examples = "\n".join([
        f"**{t['issue_type']}**: {t['template']}"
        for t in templates
    ])
    
    # Phase-specific system prompts
    if scenario == DraftScenario.REPLY:
        if phase == "unknown":
            system_prompt = f"""You are an empathetic customer support agent for an e-commerce company.

## Context
Customer: {customer_name}
Order ID: {order_id}
Current Issue: Unknown - need more details
{history_section}
## Your Task
The customer has provided their order ID but hasn't described their issue clearly. Politely ask them to describe what's wrong with their order so you can help them effectively.

## Response Guidelines
- Be warm and patient
- Thank them for providing the order information
- Make it easy for them to describe the issue (open-ended question)
- Keep it conversational and brief
- Use their name if available

## Example Tone (adapt, don't copy)
{few_shot_examples}

Generate a response that asks for issue details naturally."""

        elif phase == "pending":
            # Get action-oriented context
            action_map = {
                "refund_request": "processing your refund after verifying the details",
                "wrong_item": "arranging a replacement after verifying the details",
                "missing_item": "investigating the missing item",
                "late_delivery": "checking shipment status",
                "damaged_item": "preparing a replacement",
                "duplicate_charge": "verifying the charge",
                "defective_product": "reviewing warranty coverage",
            }
            action = action_map.get(issue_type, "reviewing your case")
            
            system_prompt = f"""You are an empathetic customer support agent for an e-commerce company.

## Context
Customer: {customer_name}
Order ID: {order_id}
Issue Type: {issue_type}
Status: Under Review (pending admin approval)
Current Action: {action}
{history_section}
## Your Task
Acknowledge the customer's issue and let them know you're actively working on it. The ticket is with our team for approval, but frame it as "we're on it" rather than "waiting for approval".

## Response Guidelines
- Be reassuring and action-oriented
- Show empathy for their situation
- Indicate active work is happening (not passive waiting)
- Keep it brief and professional
- Avoid mentioning "admin approval" or internal processes

## Example Tone and Structure
{few_shot_examples}

Generate a response that acknowledges their {issue_type} issue and shows you're actively helping."""

        elif phase == "approved":
            # Find matching template for structure guidance
            template_example = next(
                (t["template"] for t in templates if t["issue_type"] == issue_type),
                "Hi {{customer_name}}, we've reviewed order {{order_id}} and will resolve this for you."
            )
            
            system_prompt = f"""You are an empathetic customer support agent for an e-commerce company.

## Context
Customer: {customer_name}
Order ID: {order_id}
Issue Type: {issue_type}
Status: APPROVED - Resolution confirmed
{history_section}
## Your Task
Inform the customer that their issue has been resolved/approved. Be warm, reassuring, and specific about what will happen next.

## Response Guidelines
- Start with their name
- Acknowledge their issue with empathy
- Clearly state the resolution
- Be specific about next steps (refund processing, replacement shipping, etc.)
- Keep it warm but professional
- Don't over-promise timelines unless you're certain

## Template Example for {issue_type}
{template_example}

Use this template as a structural guide, but personalize it based on the conversation history and add appropriate empathy/details.

Generate a resolution confirmation response."""

        elif phase == "rejected":
            system_prompt = f"""You are an empathetic customer support agent for an e-commerce company.

## Context
Customer: {customer_name}
Order ID: {order_id}
Issue Type: {issue_type}
Status: REJECTED - Cannot proceed with request
{history_section}
## Your Task
Politely inform the customer that we're unable to proceed with their request at this time. Be respectful, brief, and direct them to check email for detailed explanation.

## Response Guidelines
- Start with their name
- Thank them for reaching out
- State clearly but gently that we cannot proceed
- Direct them to email for more details (don't explain rejection reasons in chat)
- Keep tone respectful and professional
- Don't apologize excessively

## Example Structure
"Hi [Name], thank you for reaching out about order [ID]. After reviewing your request, we're unable to proceed at this time. Please check your email for more information about this decision."

Generate a rejection response that is respectful but clear."""

    else:
        # Non-REPLY scenarios (need_identifier, order_not_found, etc.)
        candidates_str = ""
        if candidate_orders:
            candidates_str = "\n".join([
                f"- Order {o['order_id']}: {o['items'][0]['name'] if o.get('items') else 'N/A'} ({o.get('status', 'N/A')})"
                for o in candidate_orders
            ])
        
        # Build orders section if there are candidates
        orders_section = ""
        if candidates_str:
            orders_section = f"\n## Orders Found\n{candidates_str}\n"
        
        system_prompt = f"""You are a helpful customer support agent for an e-commerce company.

## Context
Scenario: {scenario.value}
Customer Message: {ticket_text}
{history_section}
## Response Guidelines by Scenario

**need_identifier**: 
- Politely ask for their order ID (format: ORD followed by numbers) OR email address
- Make it easy for them to provide information
- Be friendly and understanding

**order_not_found**: 
- Acknowledge they provided an order ID but we couldn't locate it
- Ask them to verify the order number or provide their email as alternative
- Be helpful and understanding (they might have a typo)

**no_orders_found**: 
- Acknowledge the email they provided
- Explain we couldn't find orders under that email
- Ask them to verify the email or provide order ID instead
- Remain helpful and patient

**confirm_order**: 
- List the orders found (see below)
- Ask them to specify which order they're inquiring about
- Make selection easy and clear
{orders_section}
## Tone
- Friendly and conversational
- Patient and understanding
- Professional but not robotic
- Brief and clear

## Example Templates (for tone reference)
{few_shot_examples}

Generate an appropriate response for the {scenario.value} scenario."""

    # Build user message with current context
    user_message = f"Current customer message: {ticket_text}"
    
    # Invoke LLM with system prompt and user message
    response = get_llm().invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ])
    
    return response.content.strip()


def draft_reply(state: GraphState) -> dict[str, Any]:
    """
    Unified draft node that generates responses using LLM for all scenarios.
    
    Maintains conditional flow:
    - REPLY scenario: Check phase (unknown/pending/approved/rejected)
    - Non-REPLY scenarios: Generate appropriate clarification
    
    All responses leverage:
    - Conversation history (last 5 exchanges)
    - Templates as few-shot examples
    - Customer service tone
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with draft_reply and review_status.
    """
    scenario = _coerce_draft_scenario(state.get("draft_scenario", DraftScenario.REPLY))
    issue_type = state.get("issue_type", "unknown")
    order_details = state.get("order_details")
    order_id = state.get("order_id")
    review_status = _coerce_review_status(state.get("review_status"))
    
    # Load templates for few-shot examples
    templates = load_templates()
    
    # Determine phase for REPLY scenario
    phase = None
    if scenario == DraftScenario.REPLY:
        customer_name = order_details.get("customer_name", "Customer") if order_details else "Customer"
        
        # Phase 1: Unknown issue
        if issue_type is None or issue_type == "unknown":
            phase = "unknown"
            draft = generate_draft_with_llm(scenario, phase, state, templates)
            
            return {
                "draft_reply": draft,
                "draft_scenario": DraftScenario.NEED_IDENTIFIER,
                "evidence": f"Scenario: need_issue_details, Order ID: {order_id}",
                "recommendation": "Awaiting issue details from customer",
                "messages": [AIMessage(content=draft)],
                "review_status": None,
                "sender": "draft_reply"
            }
        
        # Phase 2: PENDING
        elif review_status == ReviewStatus.PENDING or review_status is None:
            phase = "pending"
            draft = generate_draft_with_llm(scenario, phase, state, templates)
            
            evidence = f"Scenario: {scenario.value}, Issue Type: {issue_type}, Order ID: {order_id}"
            if order_details:
                evidence += f", Status: {order_details.get('status', 'N/A')}"
            
            return {
                "draft_reply": draft,
                "evidence": evidence,
                "recommendation": f"Awaiting admin approval for {issue_type} resolution",
                "messages": [AIMessage(content=draft)],
                "review_status": ReviewStatus.PENDING,
                "sender": "draft_reply"
            }
        
        # Phase 3: APPROVED
        elif review_status == ReviewStatus.APPROVED:
            phase = "approved"
            draft = generate_draft_with_llm(scenario, phase, state, templates)
            
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
        
        # Phase 4: REJECTED
        else:  # review_status == ReviewStatus.REJECTED
            phase = "rejected"
            draft = generate_draft_with_llm(scenario, phase, state, templates)
            
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
    
    # Non-REPLY scenarios: use LLM with scenario-specific prompts
    draft = generate_draft_with_llm(scenario, "non_reply", state, templates)
    
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
    Admin Review node: Checkpoint for admin approval.
    
    This node is reached after the graph resumes from interrupt.
    The review_status and admin_feedback are set externally by the API before resuming.
    
    This is a pass-through node that validates the review_status was set.
    The actual routing decision is made by route_after_admin_review, which always
    goes to draft_reply to generate the appropriate response based on review_status.
    
    Args:
        state: Current graph state.
        
    Returns:
        Partial state update with sender only (pass-through).
    """
    # Just mark that we passed through this node
    # The review_status is already set by the API
    return {
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
