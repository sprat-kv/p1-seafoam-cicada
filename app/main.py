
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import json, os, re
from uuid import uuid4
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import graph tools to load orders data
from app.graph import tools as graph_tools
from app.graph.workflow import compile_graph
from app.schema import TriageInput, TriageOutput, AdminReviewInput, ReviewAction, ReviewStatus, DraftScenario
from langgraph.checkpoint.memory import MemorySaver

app = FastAPI(title="Ticket Triage API with LangGraph HITL")

# Initialize checkpointer for HITL persistence
checkpointer = MemorySaver()

# Compile graph with checkpointer and interrupt before admin_review
hitl_graph = compile_graph(
    checkpointer=checkpointer,
    interrupt_before=["admin_review"]
)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MOCK_DIR = os.path.join(ROOT, "mock_data")

def load(name):
    with open(os.path.join(MOCK_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)

ORDERS = load("orders.json")
ISSUES = load("issues.json")
REPLIES = load("replies.json")

# Load orders into the graph tools module
graph_tools.load_orders(ORDERS)

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/orders/get")
def orders_get(order_id: str = Query(...)):
    for o in ORDERS:
        if o["order_id"] == order_id: return o
    raise HTTPException(status_code=404, detail="Order not found")

@app.get("/orders/search")
def orders_search(customer_email: str | None = None, q: str | None = None):
    matches = []
    for o in ORDERS:
        if customer_email and o["email"].lower() == customer_email.lower():
            matches.append(o)
        elif q and (o["order_id"].lower() in q.lower() or o["customer_name"].lower() in q.lower()):
            matches.append(o)
    return {"results": matches}

@app.post("/classify/issue")
def classify_issue(payload: dict):
    text = payload.get("ticket_text", "").lower()
    for rule in ISSUES:
        if rule["keyword"] in text:
            return {"issue_type": rule["issue_type"], "confidence": 0.85}
    return {"issue_type": "unknown", "confidence": 0.1}

def render_reply(issue_type: str, order):
    template = next((r["template"] for r in REPLIES if r["issue_type"] == issue_type), None)
    if not template: template = "Hi {{customer_name}}, we are reviewing order {{order_id}}."
    return template.replace("{{customer_name}}", order.get("customer_name","Customer")).replace("{{order_id}}", order.get("order_id",""))

@app.post("/reply/draft")
def reply_draft(payload: dict):
    return {"reply_text": render_reply(payload.get("issue_type"), payload.get("order", {}))}

@app.post("/triage/invoke", response_model=TriageOutput)
def triage_invoke_langgraph(body: TriageInput):
    """
    Invoke the LangGraph ticket triage workflow with HITL support.
    
    This endpoint:
    1. Starts a new triage workflow or continues an existing one
    2. Processes until it hits the admin_review interrupt (for REPLY scenarios)
    3. Returns the current state for admin review or user response
    
    Scenarios:
    - REPLY: Normal response, goes to admin review
    - NEED_IDENTIFIER: Asks user for order_id or email
    - ORDER_NOT_FOUND: Order ID not found, asks for correct info
    - NO_ORDERS_FOUND: No orders for email, asks to verify
    - CONFIRM_ORDER: Multiple orders found, asks user to pick
    """
    # Generate or use existing thread_id
    thread_id = body.thread_id or str(uuid4())
    
    # Prepare graph config with thread_id for checkpointing
    config = {"configurable": {"thread_id": thread_id}}
    
    # Prepare initial state with all fields
    initial_state = {
        "ticket_text": body.ticket_text,
        "order_id": body.order_id,
        "email": None,
        "messages": [],
        "issue_type": None,
        "order_details": None,
        "candidate_orders": None,
        "evidence": None,
        "recommendation": None,
        "draft_reply": None,
        "draft_scenario": None,
        "review_status": None,
        "admin_feedback": None,
        "sender": None,
    }
    
    try:
        # Invoke the graph - it will run until interrupt or END
        result = hitl_graph.invoke(initial_state, config)
        
        # Extract messages (convert to dict format for API response)
        messages = []
        for msg in result.get("messages", []):
            messages.append({
                "role": msg.type if hasattr(msg, "type") else "unknown",
                "content": msg.content if hasattr(msg, "content") else str(msg)
            })
        
        # Extract candidate orders summary if present
        candidate_orders = None
        if result.get("candidate_orders"):
            candidate_orders = [
                {"order_id": o.get("order_id"), "status": o.get("status"), 
                 "first_item": o["items"][0]["name"] if o.get("items") else None}
                for o in result.get("candidate_orders", [])
            ]
        
        return TriageOutput(
            thread_id=thread_id,
            order_id=result.get("order_id"),
            email=result.get("email"),
            issue_type=result.get("issue_type"),
            draft_scenario=result.get("draft_scenario"),
            draft_reply=result.get("draft_reply"),
            review_status=result.get("review_status"),
            evidence=result.get("evidence"),
            recommendation=result.get("recommendation"),
            candidate_orders=candidate_orders,
            messages=messages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing triage: {str(e)}")


@app.post("/admin/review", response_model=TriageOutput)
def admin_review_endpoint(thread_id: str, body: AdminReviewInput):
    """
    Resume the triage workflow after admin review.
    
    The admin provides a decision (approve/reject/request_changes) and optional feedback.
    The graph resumes from the interrupt and continues based on the decision.
    
    Actions:
    - APPROVED: Finalizes the response
    - REQUEST_CHANGES: Re-drafts with admin feedback
    - REJECTED: Finalizes with rejection status
    """
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # Update state with admin decision before resuming
        hitl_graph.update_state(
            config,
            {
                "review_status": body.action.status,
                "admin_feedback": body.action.feedback
            }
        )
        
        # Resume the graph with None input to continue from checkpoint
        result = hitl_graph.invoke(None, config)
        
        # Extract messages
        messages = []
        for msg in result.get("messages", []):
            messages.append({
                "role": msg.type if hasattr(msg, "type") else "unknown",
                "content": msg.content if hasattr(msg, "content") else str(msg)
            })
        
        # Extract candidate orders summary if present
        candidate_orders = None
        if result.get("candidate_orders"):
            candidate_orders = [
                {"order_id": o.get("order_id"), "status": o.get("status"), 
                 "first_item": o["items"][0]["name"] if o.get("items") else None}
                for o in result.get("candidate_orders", [])
            ]
        
        return TriageOutput(
            thread_id=thread_id,
            order_id=result.get("order_id"),
            email=result.get("email"),
            issue_type=result.get("issue_type"),
            draft_scenario=result.get("draft_scenario"),
            draft_reply=result.get("draft_reply"),
            review_status=result.get("review_status"),
            evidence=result.get("evidence"),
            recommendation=result.get("recommendation"),
            candidate_orders=candidate_orders,
            messages=messages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing admin review: {str(e)}")


# Legacy endpoints (keep for backward compatibility)
@app.post("/triage/invoke_legacy")
def triage_invoke_legacy(body: TriageInput):
    """Legacy procedural implementation for backward compatibility."""
    text = body.ticket_text
    order_id = body.order_id
    if not order_id:
        m = re.search(r"(ORD\d{4})", text, re.IGNORECASE)
        if m: order_id = m.group(1).upper()
    if not order_id: raise HTTPException(status_code=400, detail="order_id missing and not found in text")
    order = next((o for o in ORDERS if o["order_id"] == order_id), None)
    if not order: raise HTTPException(status_code=404, detail="order not found")
    issue = classify_issue({"ticket_text": text})
    reply = reply_draft({"ticket_text": text, "order": order, "issue_type": issue["issue_type"]})
    return {"order_id": order_id, "issue_type": issue["issue_type"], "order": order, "reply_text": reply["reply_text"]}
