"""
API Test Script - End-to-End HITL Flow

Tests the FastAPI endpoints for the complete HITL workflow.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_complete_hitl_flow():
    """Test complete HITL workflow via API"""
    print("\n" + "="*60)
    print("API TEST: Complete HITL Flow")
    print("="*60)
    
    # Step 1: Initial triage request
    print("\n[Step 1] Submitting initial triage request...")
    triage_payload = {
        "ticket_text": "I'd like a refund for order ORD1001. The mouse is not working.",
        "order_id": None,
        "thread_id": None
    }
    
    response = requests.post(f"{BASE_URL}/triage/invoke", json=triage_payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        thread_id = result["thread_id"]
        print(f"[OK] Thread ID: {thread_id}")
        print(f"[OK] Order ID: {result.get('order_id')}")
        print(f"[OK] Issue Type: {result.get('issue_type')}")
        print(f"[OK] Draft Reply: {result.get('draft_reply')}")
        print(f"[OK] Review Status: {result.get('review_status')}")
        
        # Step 2: Admin approves
        print("\n[Step 2] Admin approves...")
        review_payload = {
            "action": {
                "status": "approved",
                "feedback": "Looks good!"
            }
        }
        
        response2 = requests.post(
            f"{BASE_URL}/admin/review",
            params={"thread_id": thread_id},
            json=review_payload
        )
        print(f"Status: {response2.status_code}")
        
        if response2.status_code == 200:
            final_result = response2.json()
            print(f"[OK] Final Review Status: {final_result.get('review_status')}")
            print(f"[OK] Messages: {len(final_result.get('messages', []))} messages")
            print("\n[PASS] API TEST PASSED")
        else:
            print(f"[X] Admin review failed: {response2.text}")
    else:
        print(f"[X] Triage failed: {response.text}")


def test_health_check():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("API TEST: Health Check")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"[OK] Response: {response.json()}")
        print("[PASS] Health check passed")
    else:
        print(f"[X] Health check failed")


if __name__ == "__main__":
    print("\nAPI Testing Suite".center(60, " "))
    print("="*60)
    print("\nNote: Make sure the FastAPI server is running:")
    print("  uvicorn app.main:app --reload")
    print("\n" + "="*60)
    
    try:
        test_health_check()
        test_complete_hitl_flow()
        
        print("\n" + "="*60)
        print("All API tests completed successfully!".center(60, " "))
        print("="*60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n[X] ERROR: Cannot connect to API server")
        print("Please start the server with: uvicorn app.main:app --reload\n")
    except Exception as e:
        print(f"\n[X] ERROR: {e}\n")
        import traceback
        traceback.print_exc()
