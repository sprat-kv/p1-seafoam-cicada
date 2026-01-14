#!/usr/bin/env python
"""
End-to-end test script for Ticket Triage API - Phase 2 Test Cases.

Tests all scenarios from interactions/phase2_demo.json using the actual API endpoints.
Phase 2 includes more complex scenarios:
- Email-based order lookup
- Multiple orders requiring user selection
- Missing identifiers (need_identifier scenario)
- Generic questions before issue classification
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEMO_FILE = os.path.join(os.path.dirname(__file__), "interactions", "phase2_demo.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_outputs")

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
    print(f"{Colors.GREEN}[OK] {msg}{Colors.RESET}")


def print_error(msg: str):
    """Print error message."""
    print(f"{Colors.RED}[FAIL] {msg}{Colors.RESET}")


def print_info(msg: str):
    """Print info message."""
    print(f"{Colors.BLUE}[INFO] {msg}{Colors.RESET}")


def print_warning(msg: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}[WARN] {msg}{Colors.RESET}")


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
        if hasattr(e, 'response') and e.response is not None:
            try:
                print_error(f"Response: {e.response.text}")
            except:
                pass
        return None


def admin_review(thread_id: str, action: str = "approved", feedback: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Submit admin review decision."""
    payload = {
        "action": {
            "status": action,
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
        if hasattr(e, 'response') and e.response is not None:
            try:
                print_error(f"Response: {e.response.text}")
            except:
                pass
        return None


def ensure_output_dir():
    """Ensure output directory exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def validate_outcome(result: Dict[str, Any], expected: Dict[str, Any], conversation_id: str) -> bool:
    """Validate that the outcome matches expected values."""
    passed = True
    
    # Check issue_type
    expected_issue = expected.get("issue_type")
    actual_issue = result.get("issue_type")
    if expected_issue and actual_issue != expected_issue:
        print_error(f"Issue type mismatch: expected '{expected_issue}', got '{actual_issue}'")
        passed = False
    elif expected_issue:
        print_success(f"Issue type: {actual_issue}")
    
    # Check order_id (may not be set on first turn if identifier is missing)
    expected_order = expected.get("order_id")
    actual_order = result.get("order_id")
    if expected_order and actual_order and actual_order != expected_order:
        print_error(f"Order ID mismatch: expected '{expected_order}', got '{actual_order}'")
        passed = False
    elif expected_order and actual_order:
        print_success(f"Order ID: {actual_order}")
    elif expected_order and not actual_order:
        # Order ID not yet resolved - this is OK for need_identifier scenarios
        print_info(f"Order ID not yet resolved (expected: {expected_order})")
    
    return passed


def validate_response(actual_reply: str, expected_message: str) -> bool:
    """Validate that the actual response is reasonable compared to expected."""
    if not actual_reply:
        print_error("No response generated")
        return False
    
    # Simple validation - check if response has content
    has_response = len(actual_reply) > 10
    
    if has_response:
        print_success(f"Response generated ({len(actual_reply)} chars)")
        print_info(f"  Expected context: {expected_message[:80]}...")
        print_info(f"  Actual response: {actual_reply[:80]}...")
        return True
    else:
        print_error("Response too short or empty")
        return False


def extract_order_id_from_message(message: str) -> Optional[str]:
    """Extract order ID from a message if present."""
    import re
    match = re.search(r'\b(ORD\d+)\b', message, re.IGNORECASE)
    return match.group(1).upper() if match else None


def test_conversation(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single conversation from the demo file, processing all turns."""
    conversation_id = conversation.get("conversation_id", "UNKNOWN")
    turns = conversation.get("turns", [])
    expected = conversation.get("expected_outcome", {})
    
    print_header(f"Testing Conversation: {conversation_id}")
    
    # Initialize output data structure
    output_data = {
        "conversation_id": conversation_id,
        "timestamp": datetime.now().isoformat(),
        "turns": [],
        "all_passed": True,
        "turns_processed": 0
    }
    
    if not turns:
        print_warning("No turns in conversation, skipping")
        output_data["all_passed"] = False
        return output_data
    
    # Track conversation state
    thread_id = None
    all_validations_passed = True
    turn_num = 0
    resolved_order_id = None  # Track when order_id is finally resolved
    
    # Process all turns in sequence
    for i, turn in enumerate(turns):
        role = turn.get("role")
        message = turn.get("message")
        
        if not message:
            continue
        
        turn_num += 1
        print(f"\n{'-' * 70}")
        print_info(f"Turn {turn_num}: {role.upper()}")
        print(f"{'-' * 70}")
        
        if role == "user":
            print_info(f"User message: {message}")
            
            # Initialize turn data
            turn_data = {
                "turn_number": turn_num,
                "role": role,
                "user_message": message,
                "api_response": None,
                "admin_response": None,
                "validation": {}
            }
            
            # Check if user is providing an order ID (for CONFIRM_ORDER scenario)
            user_order_id = extract_order_id_from_message(message)
            if user_order_id and resolved_order_id is None:
                # User is selecting an order from multiple candidates
                print_info(f"User selected order: {user_order_id}")
                resolved_order_id = user_order_id
            
            # Invoke triage with the user message
            print_info("Invoking triage endpoint...")
            result = invoke_triage(
                ticket_text=message,
                order_id=user_order_id,  # Pass if user explicitly provided
                thread_id=thread_id
            )
            
            if not result:
                print_error("Triage invocation failed")
                all_validations_passed = False
                turn_data["validation"]["triage_invocation"] = {"passed": False}
                output_data["turns"].append(turn_data)
                continue
            
            # Extract thread_id for subsequent turns
            if not thread_id:
                thread_id = result.get("thread_id")
                print_info(f"Thread ID: {thread_id}")
            
            # Update resolved_order_id if we got one
            if result.get("order_id") and not resolved_order_id:
                resolved_order_id = result.get("order_id")
            
            # Display results
            print_info("Triage Results:")
            print(f"  Thread ID: {result.get('thread_id')}")
            print(f"  Order ID: {result.get('order_id', 'None')}")
            print(f"  Issue Type: {result.get('issue_type', 'None')}")
            print(f"  Draft Scenario: {result.get('draft_scenario', 'None')}")
            print(f"  Review Status: {result.get('review_status', 'None')}")
            if result.get("draft_reply"):
                draft_preview = result.get("draft_reply", "")[:80] + "..."
                print(f"  Draft Reply: {draft_preview}")
            
            turn_data["api_response"] = result
            
            # Validate expected outcome (only on first turn or when order is resolved)
            if turn_num == 1 or (resolved_order_id and result.get("order_id") == resolved_order_id):
                print_info("Validating expected outcome...")
                validation_passed = validate_outcome(result, expected, conversation_id)
                turn_data["validation"]["outcome"] = {"passed": validation_passed}
                if not validation_passed:
                    all_validations_passed = False
            
            # Handle different scenarios
            scenario = result.get("draft_scenario")
            review_status = result.get("review_status")
            
            if scenario == "reply" and review_status == "pending":
                # REPLY scenario - needs admin review
                print_info("Testing admin review (APPROVED)...")
                admin_result = admin_review(thread_id, action="approved")
                
                if admin_result:
                    print_success("Admin review completed")
                    print(f"  Final Review Status: {admin_result.get('review_status')}")
                    if admin_result.get("draft_reply"):
                        final_preview = admin_result.get("draft_reply", "")[:80] + "..."
                        print(f"  Final Reply: {final_preview}")
                    
                    turn_data["admin_response"] = admin_result
                    
                    # Validate assistant response
                    expected_assistant = None
                    if i + 1 < len(turns):
                        next_turn = turns[i + 1]
                        if next_turn.get("role") == "assistant":
                            expected_assistant = next_turn.get("message")
                    
                    if expected_assistant:
                        actual_reply = admin_result.get("draft_reply", "")
                        response_valid = validate_response(actual_reply, expected_assistant)
                        turn_data["validation"]["response"] = {"passed": response_valid}
                        if not response_valid:
                            all_validations_passed = False
                else:
                    print_error("Admin review failed")
                    all_validations_passed = False
                    turn_data["validation"]["admin_review"] = {"passed": False}
            
            elif scenario in ("need_identifier", "order_not_found", "no_orders_found", "confirm_order"):
                # Non-REPLY scenarios - no admin review needed
                print_info(f"Scenario: {scenario} (no admin review needed)")
                
                # Validate assistant response
                expected_assistant = None
                if i + 1 < len(turns):
                    next_turn = turns[i + 1]
                    if next_turn.get("role") == "assistant":
                        expected_assistant = next_turn.get("message")
                
                if expected_assistant and result.get("draft_reply"):
                    actual_reply = result.get("draft_reply", "")
                    response_valid = validate_response(actual_reply, expected_assistant)
                    turn_data["validation"]["response"] = {"passed": response_valid}
                    if not response_valid:
                        all_validations_passed = False
                elif expected_assistant:
                    print_warning("Expected assistant message but no draft_reply generated")
                    all_validations_passed = False
                    turn_data["validation"]["response"] = {"passed": False}
            
            output_data["turns"].append(turn_data)
        
        elif role == "assistant":
            print_info(f"Expected assistant message: {message}")
            print_info("(Validation done in previous turn)")
            
            # Record expected message for reference
            turn_data = {
                "turn_number": turn_num,
                "role": role,
                "expected_message": message
            }
            output_data["turns"].append(turn_data)
    
    # Summary
    print(f"\n{'-' * 70}")
    print_info(f"Conversation Summary: Processed {turn_num} turns")
    if all_validations_passed:
        print_success(f"All validations passed for {conversation_id}")
    else:
        print_error(f"Some validations failed for {conversation_id}")
    print(f"{'-' * 70}")
    
    output_data["all_passed"] = all_validations_passed
    output_data["turns_processed"] = turn_num
    
    # Save conversation output
    save_conversation_output(output_data)
    
    return output_data


def save_conversation_output(conversation_data: Dict[str, Any]):
    """Save conversation output to files."""
    ensure_output_dir()
    
    conversation_id = conversation_data.get("conversation_id", "UNKNOWN")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON
    json_file = os.path.join(OUTPUT_DIR, f"{conversation_id}_{timestamp}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(conversation_data, f, indent=2, ensure_ascii=False)
    print_info(f"Saved JSON output: {json_file}")
    
    # Save text
    text_file = os.path.join(OUTPUT_DIR, f"{conversation_id}_{timestamp}.txt")
    with open(text_file, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write(f"CONVERSATION: {conversation_id}\n")
        f.write(f"Timestamp: {conversation_data.get('timestamp')}\n")
        f.write("=" * 70 + "\n\n")
        
        for turn in conversation_data.get("turns", []):
            f.write(f"Turn {turn.get('turn_number', '?')}: {turn.get('role', 'unknown').upper()}\n")
            f.write("-" * 70 + "\n")
            
            if turn.get("user_message"):
                f.write(f"User: {turn['user_message']}\n\n")
            
            if turn.get("api_response"):
                api = turn["api_response"]
                f.write("Triage Response:\n")
                f.write(f"  Thread ID: {api.get('thread_id')}\n")
                f.write(f"  Order ID: {api.get('order_id', 'None')}\n")
                f.write(f"  Issue Type: {api.get('issue_type', 'None')}\n")
                f.write(f"  Draft Scenario: {api.get('draft_scenario', 'None')}\n")
                f.write(f"  Review Status: {api.get('review_status', 'None')}\n")
                if api.get("draft_reply"):
                    f.write(f"  Draft Reply: {api['draft_reply']}\n")
                f.write("\n")
            
            if turn.get("admin_response"):
                admin = turn["admin_response"]
                f.write("Admin Review Response:\n")
                f.write(f"  Review Status: {admin.get('review_status', 'N/A')}\n")
                if admin.get("draft_reply"):
                    f.write(f"  Final Reply: {admin['draft_reply']}\n")
                f.write("\n")
            
            if turn.get("expected_message"):
                f.write(f"Expected Assistant Message: {turn['expected_message']}\n\n")
            
            if turn.get("validation"):
                f.write("Validation Results:\n")
                for key, value in turn["validation"].items():
                    status = "[OK] PASS" if value.get("passed") else "[FAIL] FAIL"
                    f.write(f"  {status}: {key}\n")
                f.write("\n")
            
            f.write("\n")
        
        f.write(f"{'=' * 70}\n")
        f.write(f"Summary: Processed {conversation_data.get('turns_processed', 0)} turns\n")
        f.write(f"All Validations Passed: {conversation_data.get('all_passed', False)}\n")
    
    print_info(f"Saved text output: {text_file}")


def save_test_summary(all_conversations: List[Dict[str, Any]]):
    """Save overall test summary."""
    ensure_output_dir()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "test_file": "phase2_demo.json",
        "total_conversations": len(all_conversations),
        "passed": sum(1 for c in all_conversations if c.get("all_passed")),
        "failed": sum(1 for c in all_conversations if not c.get("all_passed")),
        "conversations": [
            {
                "conversation_id": c.get("conversation_id"),
                "passed": c.get("all_passed"),
                "turns_processed": c.get("turns_processed", 0)
            }
            for c in all_conversations
        ]
    }
    
    # Save JSON summary
    json_file = os.path.join(OUTPUT_DIR, f"phase2_test_summary_{timestamp}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Save text summary
    text_file = os.path.join(OUTPUT_DIR, f"phase2_test_summary_{timestamp}.txt")
    with open(text_file, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("PHASE 2 TEST SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Timestamp: {summary['timestamp']}\n")
        f.write(f"Test File: {summary['test_file']}\n")
        f.write(f"Total Conversations: {summary['total_conversations']}\n")
        f.write(f"Passed: {summary['passed']}\n")
        f.write(f"Failed: {summary['failed']}\n\n")
        f.write("Conversations:\n")
        f.write("-" * 70 + "\n")
        for conv in summary["conversations"]:
            status = "PASS" if conv["passed"] else "FAIL"
            f.write(f"{status} - {conv['conversation_id']} ({conv['turns_processed']} turns)\n")
    
    print_info(f"Saved test summary: {json_file} and {text_file}")


def main():
    """Main test execution."""
    print_header("Ticket Triage API - Phase 2 End-to-End Tests")
    
    # Check environment
    print_info("Checking environment variables...")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print_error("OPENAI_API_KEY not found in environment")
        print_info("Please set OPENAI_API_KEY in your .env file")
        print_info("Run: python check_env.py to verify your setup")
        sys.exit(1)
    else:
        masked_key = openai_key[:7] + "..." + openai_key[-4:] if len(openai_key) > 11 else "***"
        print_success(f"OPENAI_API_KEY found: {masked_key}")
    print()
    
    # Check API health
    print_info("Checking API health...")
    if not check_api_health():
        sys.exit(1)
    
    # Load test cases
    print_info(f"Loading test cases from {DEMO_FILE}...")
    try:
        with open(DEMO_FILE, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        print_success(f"Loaded {len(conversations)} test conversations")
    except FileNotFoundError:
        print_error(f"Test file not found: {DEMO_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in test file: {e}")
        sys.exit(1)
    
    # Run tests
    all_conversations = []
    for idx, conversation in enumerate(conversations, 1):
        print(f"\n[{idx}/{len(conversations)}]")
        result = test_conversation(conversation)
        all_conversations.append(result)
        time.sleep(0.5)  # Small delay between conversations
    
    # Summary
    print_header("Test Summary")
    print()
    
    total = len(all_conversations)
    passed = sum(1 for c in all_conversations if c.get("all_passed"))
    failed = total - passed
    
    print(f"Total Tests: {total}")
    if passed == total:
        print_success(f"Passed: {passed}")
    else:
        print_success(f"Passed: {passed}")
        print_error(f"Failed: {failed}")
    
    print()
    print("Detailed Results:")
    for conv in all_conversations:
        status = "PASS" if conv.get("all_passed") else "FAIL"
        print(f"  {Colors.GREEN if conv.get('all_passed') else Colors.RED}{status}{Colors.RESET} - {conv.get('conversation_id')}")
    
    # Save summary
    save_test_summary(all_conversations)
    
    print()
    print_info("All conversation outputs saved to: " + OUTPUT_DIR)
    print()
    
    if passed == total:
        print_success("All tests passed!")
        sys.exit(0)
    else:
        print_error("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
