"""
Test script for Stage 3: Admin Review & HITL

This script verifies:
1. Graph pauses at admin_review interrupt
2. Admin can approve/reject/request changes
3. Graph resumes correctly based on admin decision
4. Full HITL workflow end-to-end
"""

import json
import os
from uuid import uuid4
from app.graph.workflow import compile_graph
from app.graph import tools as graph_tools
from app.schema import ReviewStatus
from langgraph.checkpoint.memory import MemorySaver

# Load mock data
ROOT = os.path.abspath(os.path.dirname(__file__))
MOCK_DIR = os.path.join(ROOT, "mock_data")

def load_json(name):
    with open(os.path.join(MOCK_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)

ORDERS = load_json("orders.json")

# Initialize graph tools with orders data
graph_tools.load_orders(ORDERS)

# Compile graph with checkpointer and interrupt
checkpointer = MemorySaver()
hitl_graph = compile_graph(
    checkpointer=checkpointer,
    interrupt_before=["admin_review"]
)


def test_case_1_approve():
    """Test: Admin approves the draft reply"""
    print("\n" + "="*60)
    print("TEST CASE 1: Admin APPROVES draft reply")
    print("="*60)
    
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Step 1: Initial invocation - should pause at admin_review
    initial_state = {
        "ticket_text": "I'd like a refund for order ORD1001. The mouse is not working.",
        "order_id": None,
        "messages": [],
        "issue_type": None,
        "order_details": None,
        "evidence": None,
        "recommendation": None,
        "draft_reply": None,
        "review_status": ReviewStatus.PENDING,
        "admin_feedback": None,
        "sender": None,
    }
    
    print("\n[Step 1] Invoking graph (should pause at admin_review)...")
    result = hitl_graph.invoke(initial_state, config)
    
    print(f"[OK] Paused at node: {result.get('sender')}")
    print(f"[OK] Draft reply: {result.get('draft_reply')}")
    print(f"[OK] Review status: {result.get('review_status')}")
    
    # Check that we paused before admin_review
    assert result.get('sender') == 'draft_reply', "Should have paused after draft_reply"
    assert result.get('draft_reply') is not None, "Should have draft reply"
    
    # Step 2: Admin approves - update state before resuming
    print("\n[Step 2] Admin APPROVES...")
    
    # Update the state with admin decision
    hitl_graph.update_state(
        config,
        {
            "review_status": ReviewStatus.APPROVED,
            "admin_feedback": "Looks good!"
        }
    )
    
    # Resume the graph with None input to continue from checkpoint
    final_result = hitl_graph.invoke(None, config)
    
    print(f"[OK] Final node: {final_result.get('sender')}")
    print(f"[OK] Review status: {final_result.get('review_status')}")
    print(f"[OK] Messages count: {len(final_result.get('messages', []))}")
    
    # Assertions
    assert final_result.get('sender') == 'final_response', "Should end at final_response"
    assert final_result.get('review_status') == ReviewStatus.APPROVED, "Should be approved"
    
    print("\n[PASS] TEST CASE 1 PASSED")


def test_case_2_request_changes():
    """Test: Admin requests changes to the draft"""
    print("\n" + "="*60)
    print("TEST CASE 2: Admin REQUESTS CHANGES")
    print("="*60)
    
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Step 1: Initial invocation
    initial_state = {
        "ticket_text": "My order ORD1002 has not arrived yet. Where is it?",
        "order_id": None,
        "messages": [],
        "issue_type": None,
        "order_details": None,
        "evidence": None,
        "recommendation": None,
        "draft_reply": None,
        "review_status": ReviewStatus.PENDING,
        "admin_feedback": None,
        "sender": None,
    }
    
    print("\n[Step 1] Invoking graph...")
    result = hitl_graph.invoke(initial_state, config)
    
    print(f"[OK] Paused at: {result.get('sender')}")
    print(f"[OK] Draft reply: {result.get('draft_reply')}")
    
    # Step 2: Admin requests changes
    print("\n[Step 2] Admin REQUESTS CHANGES...")
    
    # Update state with admin decision
    hitl_graph.update_state(
        config,
        {
            "review_status": ReviewStatus.REQUEST_CHANGES,
            "admin_feedback": "Please add tracking number"
        }
    )
    
    # Resume - should go back to draft_reply and pause again
    result2 = hitl_graph.invoke(None, config)
    
    print(f"[OK] After changes request, node: {result2.get('sender')}")
    print(f"[OK] Updated draft: {result2.get('draft_reply')}")
    
    # Should have re-drafted and paused again
    assert result2.get('sender') == 'draft_reply', "Should redraft and pause again"
    assert "tracking number" in result2.get('draft_reply', '').lower() or \
           "admin note" in result2.get('draft_reply', '').lower(), "Should incorporate feedback"
    
    # Step 3: Admin approves the updated draft
    print("\n[Step 3] Admin APPROVES updated draft...")
    
    # Update state
    hitl_graph.update_state(
        config,
        {"review_status": ReviewStatus.APPROVED}
    )
    
    # Resume
    final_result = hitl_graph.invoke(None, config)
    
    print(f"[OK] Final node: {final_result.get('sender')}")
    
    assert final_result.get('sender') == 'final_response', "Should complete successfully"
    
    print("\n[PASS] TEST CASE 2 PASSED")


def test_case_3_reject():
    """Test: Admin rejects and restarts from classification"""
    print("\n" + "="*60)
    print("TEST CASE 3: Admin REJECTS (restart classification)")
    print("="*60)
    
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Step 1: Initial invocation
    initial_state = {
        "ticket_text": "I need help with my order ORD1004. It's broken.",
        "order_id": None,
        "messages": [],
        "issue_type": None,
        "order_details": None,
        "evidence": None,
        "recommendation": None,
        "draft_reply": None,
        "review_status": ReviewStatus.PENDING,
        "admin_feedback": None,
        "sender": None,
    }
    
    print("\n[Step 1] Invoking graph...")
    result = hitl_graph.invoke(initial_state, config)
    
    print(f"[OK] Paused at: {result.get('sender')}")
    print(f"[OK] Issue type: {result.get('issue_type')}")
    
    # Step 2: Admin rejects
    print("\n[Step 2] Admin REJECTS (wrong classification)...")
    
    # Update state
    hitl_graph.update_state(
        config,
        {
            "review_status": ReviewStatus.REJECTED,
            "admin_feedback": "Wrong issue type - should be refund"
        }
    )
    
    # Resume - should go back to classify_issue and pause again
    result2 = hitl_graph.invoke(None, config)
    
    print(f"[OK] After rejection, node: {result2.get('sender')}")
    
    # Should have re-classified and paused again at draft
    assert result2.get('sender') in ['classify_issue', 'draft_reply'], "Should reclassify"
    
    print("\n[PASS] TEST CASE 3 PASSED")


if __name__ == "__main__":
    print("\n" + "STAGE 3 HITL VERIFICATION TEST SUITE".center(60, " "))
    print("="*60)
    
    try:
        test_case_1_approve()
        test_case_2_request_changes()
        test_case_3_reject()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED! STAGE 3 COMPLETE".center(60, " "))
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n[X] TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n[X] ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        raise
