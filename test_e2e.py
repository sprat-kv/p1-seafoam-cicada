#!/usr/bin/env python
"""
End-to-end test script for Ticket Triage API.

Tests all scenarios from interactions/phase1_demo.json using the actual API endpoints.
"""

import json
import os
import sys
import time
from typing import Dict, Any, Optional
import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEMO_FILE = os.path.join(os.path.dirname(__file__), "interactions", "phase1_demo.json")

# Colors for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_success(msg: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


def print_warning(msg: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def print_header(msg: str):
    """Print header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def check_api_health() -> bool:
    """Check if API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("API is running and healthy")
            return True
        else:
            print_error(f"API health check failed: {response.status_code}")
            return False
    except RequestException as e:
        print_error(f"Cannot connect to API at {API_BASE_URL}")
        print_info("Make sure the server is running: uvicorn app.main:app --reload")
        return False


def invoke_triage(ticket_text: str, order_id: Optional[str] = None, thread_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Invoke the triage endpoint."""
    payload = {
        "ticket_text": ticket_text,
        "order_id": order_id,
        "thread_id": thread_id
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/triage/invoke",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        print_error(f"Triage invocation failed: {e}")
        if hasattr(e.response, 'text'):
            print_error(f"Response: {e.response.text}")
        return None


def admin_review(thread_id: str, status: str, feedback: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Submit admin review decision."""
    payload = {
        "action": {
            "status": status,
            "feedback": feedback
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/admin/review",
            params={"thread_id": thread_id},
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        print_error(f"Admin review failed: {e}")
        if hasattr(e.response, 'text'):
            print_error(f"Response: {e.response.text}")
        return None


def validate_outcome(result: Dict[str, Any], expected: Dict[str, Any], conversation_id: str) -> bool:
    """Validate the outcome against expected values."""
    all_passed = True
    
    # Check issue_type
    if "issue_type" in expected:
        actual_issue = result.get("issue_type")
        expected_issue = expected["issue_type"]
        if actual_issue == expected_issue:
            print_success(f"Issue type: {actual_issue}")
        else:
            print_error(f"Issue type mismatch: expected '{expected_issue}', got '{actual_issue}'")
            all_passed = False
    
    # Check order_id
    if "order_id" in expected:
        actual_order = result.get("order_id")
        expected_order = expected["order_id"]
        if actual_order == expected_order:
            print_success(f"Order ID: {actual_order}")
        else:
            print_error(f"Order ID mismatch: expected '{expected_order}', got '{actual_order}'")
            all_passed = False
    
    return all_passed


def test_conversation(conversation: Dict[str, Any]) -> bool:
    """Test a single conversation from the demo file."""
    conversation_id = conversation.get("conversation_id", "UNKNOWN")
    turns = conversation.get("turns", [])
    expected = conversation.get("expected_outcome", {})
    
    print_header(f"Testing Conversation: {conversation_id}")
    
    if not turns:
        print_warning("No turns in conversation, skipping")
        return False
    
    # Get the first user message
    first_user_message = None
    for turn in turns:
        if turn.get("role") == "user":
            first_user_message = turn.get("message")
            break
    
    if not first_user_message:
        print_warning("No user message found, skipping")
        return False
    
    print_info(f"User message: {first_user_message}")
    
    # Invoke triage
    print_info("Invoking triage endpoint...")
    result = invoke_triage(first_user_message)
    
    if not result:
        print_error("Triage invocation failed")
        return False
    
    # Display results
    print_info("Triage Results:")
    print(f"  Thread ID: {result.get('thread_id')}")
    print(f"  Order ID: {result.get('order_id', 'None')}")
    print(f"  Issue Type: {result.get('issue_type', 'None')}")
    print(f"  Draft Scenario: {result.get('draft_scenario', 'None')}")
    print(f"  Review Status: {result.get('review_status', 'None')}")
    
    if result.get("draft_reply"):
        draft_preview = result["draft_reply"][:100] + "..." if len(result["draft_reply"]) > 100 else result["draft_reply"]
        print(f"  Draft Reply: {draft_preview}")
    
    # Validate outcome
    print_info("Validating expected outcome...")
    validation_passed = validate_outcome(result, expected, conversation_id)
    
    # If REPLY scenario, test admin review
    if result.get("draft_scenario") == "reply" and result.get("review_status") == "pending":
        print_info("Testing admin review (APPROVED)...")
        thread_id = result.get("thread_id")
        
        if thread_id:
            admin_result = admin_review(thread_id, "approved", "Test approval")
            
            if admin_result:
                print_success("Admin review completed")
                print(f"  Final Review Status: {admin_result.get('review_status')}")
                if admin_result.get("draft_reply"):
                    final_preview = admin_result["draft_reply"][:100] + "..." if len(admin_result["draft_reply"]) > 100 else admin_result["draft_reply"]
                    print(f"  Final Reply: {final_preview}")
            else:
                print_error("Admin review failed")
                validation_passed = False
    
    return validation_passed


def main():
    """Main test runner."""
    print_header("Ticket Triage API - End-to-End Tests")
    
    # Check environment variables
    print_info("Checking environment variables...")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print_error("OPENAI_API_KEY not found in environment")
        print_info("Make sure you have:")
        print_info("  1. Created .env file: cp .env.example .env")
        print_info("  2. Added your OPENAI_API_KEY to .env")
        print_info("  3. Restarted the API server after creating .env")
        sys.exit(1)
    else:
        masked_key = openai_key[:7] + "..." + openai_key[-4:] if len(openai_key) > 11 else "***"
        print_success(f"OPENAI_API_KEY found: {masked_key}")
    print()
    
    # Check API health
    print_info("Checking API health...")
    if not check_api_health():
        sys.exit(1)
    
    # Load demo conversations
    print_info(f"Loading test cases from {DEMO_FILE}...")
    try:
        with open(DEMO_FILE, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        print_success(f"Loaded {len(conversations)} test conversations")
    except FileNotFoundError:
        print_error(f"Demo file not found: {DEMO_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in demo file: {e}")
        sys.exit(1)
    
    # Run tests
    results = []
    for i, conversation in enumerate(conversations, 1):
        print(f"\n[{i}/{len(conversations)}]")
        passed = test_conversation(conversation)
        results.append({
            "conversation_id": conversation.get("conversation_id", f"TEST-{i}"),
            "passed": passed
        })
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print_header("Test Summary")
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    
    print(f"\nTotal Tests: {total_count}")
    print_success(f"Passed: {passed_count}")
    if passed_count < total_count:
        print_error(f"Failed: {total_count - passed_count}")
    
    print("\nDetailed Results:")
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        color = Colors.GREEN if result["passed"] else Colors.RED
        print(f"  {color}{status}{Colors.RESET} - {result['conversation_id']}")
    
    # Exit code
    if passed_count == total_count:
        print_success("\nAll tests passed!")
        sys.exit(0)
    else:
        print_error(f"\n{total_count - passed_count} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
