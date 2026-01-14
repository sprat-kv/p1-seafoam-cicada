"""Quick test for the conditional flow."""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_approval_flow():
    print("=" * 60)
    print("Testing Conditional HITL Flow - APPROVAL")
    print("=" * 60)
    
    # Step 1: Initial triage - should return PENDING
    print("\n1. Initial triage request...")
    response = requests.post(
        f"{BASE_URL}/triage/invoke",
        json={"ticket_text": "Wrong item shipped for order ORD1006"}
    )
    result = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Thread ID: {result.get('thread_id')}")
    print(f"   Issue Type: {result.get('issue_type')}")
    print(f"   Draft Scenario: {result.get('draft_scenario')}")
    print(f"   Review Status: {result.get('review_status')}")
    print(f"   Suggested Action: {result.get('suggested_action')[:50]}..." if result.get('suggested_action') else "   Suggested Action: None")
    print(f"   Draft Reply: {result.get('draft_reply')[:80]}..." if result.get('draft_reply') else "   Draft Reply: None")
    
    thread_id = result.get("thread_id")
    
    # Verify it's pending
    if result.get("review_status") != "pending":
        print(f"   ERROR: Expected 'pending', got '{result.get('review_status')}'")
        return False
    print("   [OK] First run correctly returns PENDING status")
    
    # Step 2: Check pending tickets
    print("\n2. Check pending tickets...")
    response = requests.get(f"{BASE_URL}/admin/review")
    pending = response.json()
    print(f"   Pending count: {pending.get('pending_count')}")
    if pending.get('pending_count') > 0:
        print(f"   First ticket thread_id: {pending.get('tickets', [{}])[0].get('thread_id')}")
    
    # Step 3: Admin approves
    print("\n3. Admin approves the action...")
    response = requests.post(
        f"{BASE_URL}/admin/review?thread_id={thread_id}",
        json={"action": {"status": "approved", "feedback": "Looks good, proceed with replacement"}}
    )
    result = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Review Status: {result.get('review_status')}")
    print(f"   Draft Reply: {result.get('draft_reply')[:100]}..." if result.get('draft_reply') else "   Draft Reply: None")
    
    # Verify it's approved
    if result.get("review_status") != "approved":
        print(f"   ERROR: Expected 'approved', got '{result.get('review_status')}'")
        return False
    print("   [OK] Second run correctly returns APPROVED status with LLM response")
    
    # Step 4: Check pending tickets cleared
    print("\n4. Check pending tickets cleared...")
    response = requests.get(f"{BASE_URL}/admin/review")
    pending = response.json()
    print(f"   Pending count: {pending.get('pending_count')}")
    if pending.get('pending_count') == 0:
        print("   [OK] Ticket removed from pending list")
    else:
        print("   WARNING: Ticket still in pending list")
    
    return True


def test_rejection_flow():
    print("\n" + "=" * 60)
    print("Testing Conditional HITL Flow - REJECTION")
    print("=" * 60)
    
    # Step 1: Initial triage - should return PENDING
    print("\n1. Initial triage request...")
    response = requests.post(
        f"{BASE_URL}/triage/invoke",
        json={"ticket_text": "I want a refund for order ORD1001"}
    )
    result = response.json()
    thread_id = result.get("thread_id")
    print(f"   Thread ID: {thread_id}")
    print(f"   Issue Type: {result.get('issue_type')}")
    print(f"   Review Status: {result.get('review_status')}")
    
    # Step 2: Admin rejects
    print("\n2. Admin rejects the action...")
    response = requests.post(
        f"{BASE_URL}/admin/review?thread_id={thread_id}",
        json={"action": {"status": "rejected", "feedback": "Order delivered correctly"}}
    )
    result = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Review Status: {result.get('review_status')}")
    print(f"   Draft Reply: {result.get('draft_reply')[:100]}..." if result.get('draft_reply') else "   Draft Reply: None")
    
    # Verify it's rejected
    if result.get("review_status") != "rejected":
        print(f"   ERROR: Expected 'rejected', got '{result.get('review_status')}'")
        return False
    print("   [OK] Rejection flow works correctly")
    
    return True


def test_non_reply_scenario():
    print("\n" + "=" * 60)
    print("Testing Non-REPLY Scenario (no admin needed)")
    print("=" * 60)
    
    # Test NEED_IDENTIFIER scenario
    print("\n1. Request without order ID...")
    response = requests.post(
        f"{BASE_URL}/triage/invoke",
        json={"ticket_text": "I have a problem with my order"}
    )
    result = response.json()
    print(f"   Draft Scenario: {result.get('draft_scenario')}")
    print(f"   Review Status: {result.get('review_status')}")
    print(f"   Draft Reply: {result.get('draft_reply')[:80]}..." if result.get('draft_reply') else "   Draft Reply: None")
    
    # Should be need_identifier and no review_status
    if result.get("draft_scenario") == "need_identifier":
        print("   [OK] NEED_IDENTIFIER scenario handled without admin")
    else:
        print(f"   NOTE: Got scenario {result.get('draft_scenario')}")
    
    return True


if __name__ == "__main__":
    try:
        all_passed = True
        all_passed = test_approval_flow() and all_passed
        all_passed = test_rejection_flow() and all_passed
        all_passed = test_non_reply_scenario() and all_passed
        
        print("\n" + "=" * 60)
        if all_passed:
            print("All tests completed successfully!")
        else:
            print("Some tests failed!")
        print("=" * 60)
        exit(0 if all_passed else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
