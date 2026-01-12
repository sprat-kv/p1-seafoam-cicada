"""
Test script for Stage 2: Core Logic & Nodes

This script verifies:
1. Order ID extraction from ticket text
2. Issue classification
3. Order fetching via tool
4. Reply drafting
5. End-to-end flow without HITL
"""

import json
import os
from app.graph.workflow import compile_graph
from app.graph import tools as graph_tools

# Load mock data
ROOT = os.path.abspath(os.path.dirname(__file__))
MOCK_DIR = os.path.join(ROOT, "mock_data")

def load_json(name):
    with open(os.path.join(MOCK_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)

ORDERS = load_json("orders.json")

# Initialize graph tools with orders data
graph_tools.load_orders(ORDERS)

# Compile graph without checkpointer for testing
graph = compile_graph()

def test_case_1():
    """Test: Refund request with order ID in text"""
    print("\n" + "="*60)
    print("TEST CASE 1: Refund request for order ORD1001")
    print("="*60)
    
    initial_state = {
        "ticket_text": "I'd like a refund for order ORD1001. The mouse is not working.",
        "order_id": None,
        "messages": [],
        "issue_type": None,
        "order_details": None,
        "evidence": None,
        "recommendation": None,
        "draft_reply": None,
        "review_status": "pending",
        "admin_feedback": None,
        "sender": None,
    }
    
    result = graph.invoke(initial_state)
    
    print(f"\n[OK] Order ID extracted: {result.get('order_id')}")
    print(f"[OK] Issue classified as: {result.get('issue_type')}")
    print(f"[OK] Order details fetched: {result.get('order_details', {}).get('customer_name')}")
    print(f"[OK] Draft reply:\n  {result.get('draft_reply')}")
    print(f"[OK] Evidence: {result.get('evidence')}")
    print(f"[OK] Recommendation: {result.get('recommendation')}")
    
    # Assertions
    assert result.get('order_id') == 'ORD1001', "Order ID not extracted correctly"
    assert result.get('issue_type') == 'refund_request', "Issue not classified correctly"
    assert result.get('order_details') is not None, "Order details not fetched"
    assert 'Ava Chen' in result.get('draft_reply', ''), "Customer name not in draft"
    
    print("\n[PASS] TEST CASE 1 PASSED")


def test_case_2():
    """Test: Late delivery with order ID in parentheses"""
    print("\n" + "="*60)
    print("TEST CASE 2: Late delivery for order ORD1002")
    print("="*60)
    
    initial_state = {
        "ticket_text": "My Bluetooth speaker (ORD1002) has not arrived yet.",
        "order_id": None,
        "messages": [],
        "issue_type": None,
        "order_details": None,
        "evidence": None,
        "recommendation": None,
        "draft_reply": None,
        "review_status": "pending",
        "admin_feedback": None,
        "sender": None,
    }
    
    result = graph.invoke(initial_state)
    
    print(f"\n[OK] Order ID extracted: {result.get('order_id')}")
    print(f"[OK] Issue classified as: {result.get('issue_type')}")
    print(f"[OK] Draft reply:\n  {result.get('draft_reply')}")
    
    # Assertions
    assert result.get('order_id') == 'ORD1002', "Order ID not extracted correctly"
    assert result.get('issue_type') == 'late_delivery', "Issue not classified correctly"
    assert 'David Lee' in result.get('draft_reply', ''), "Customer name not in draft"
    
    print("\n[PASS] TEST CASE 2 PASSED")


def test_case_3():
    """Test: Order ID provided explicitly (not in text)"""
    print("\n" + "="*60)
    print("TEST CASE 3: Defective product with explicit order ID")
    print("="*60)
    
    initial_state = {
        "ticket_text": "The smart watch I got is not working.",
        "order_id": "ORD1004",  # Provided explicitly
        "messages": [],
        "issue_type": None,
        "order_details": None,
        "evidence": None,
        "recommendation": None,
        "draft_reply": None,
        "review_status": "pending",
        "admin_feedback": None,
        "sender": None,
    }
    
    result = graph.invoke(initial_state)
    
    print(f"\n[OK] Order ID used: {result.get('order_id')}")
    print(f"[OK] Issue classified as: {result.get('issue_type')}")
    print(f"[OK] Draft reply:\n  {result.get('draft_reply')}")
    
    # Assertions
    assert result.get('order_id') == 'ORD1004', "Order ID not preserved"
    assert result.get('issue_type') == 'defective_product', "Issue not classified correctly"
    assert 'John Smith' in result.get('draft_reply', ''), "Customer name not in draft"
    
    print("\n[PASS] TEST CASE 3 PASSED")


def test_case_4():
    """Test: No order ID - should end early"""
    print("\n" + "="*60)
    print("TEST CASE 4: Missing order ID (should end early)")
    print("="*60)
    
    initial_state = {
        "ticket_text": "I have a problem with my order but I don't remember the order number.",
        "order_id": None,
        "messages": [],
        "issue_type": None,
        "order_details": None,
        "evidence": None,
        "recommendation": None,
        "draft_reply": None,
        "review_status": "pending",
        "admin_feedback": None,
        "sender": None,
    }
    
    result = graph.invoke(initial_state)
    
    print(f"\n[OK] Order ID extracted: {result.get('order_id')}")
    print(f"[OK] Sender: {result.get('sender')}")
    print(f"[OK] Draft reply: {result.get('draft_reply')}")
    
    # Assertions
    assert result.get('order_id') is None, "Should not have extracted order ID"
    assert result.get('sender') == 'ingest', "Should have stopped at ingest node"
    assert result.get('draft_reply') is None, "Should not have drafted reply"
    
    print("\n[PASS] TEST CASE 4 PASSED")


if __name__ == "__main__":
    print("\n" + "STAGE 2 VERIFICATION TEST SUITE".center(60, " "))
    print("="*60)
    
    try:
        test_case_1()
        test_case_2()
        test_case_3()
        test_case_4()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED! STAGE 2 COMPLETE".center(60, " "))
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n[X] TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n[X] ERROR: {e}\n")
        raise
