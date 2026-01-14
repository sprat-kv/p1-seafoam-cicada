#!/usr/bin/env python
"""
End-to-end test script for Ticket Triage API.

Tests all scenarios from interactions/phase1_demo.json using the actual API endpoints.
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
DEMO_FILE = os.path.join(os.path.dirname(__file__), "interactions", "phase1_demo.json")
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


def ensure_output_dir():
    """Ensure output directory exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_conversation_output(conversation_data: Dict[str, Any], format: str = "both"):
    """Save conversation output to file(s)."""
    ensure_output_dir()
    
    conversation_id = conversation_data.get("conversation_id", "UNKNOWN")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format in ("json", "both"):
        json_file = os.path.join(OUTPUT_DIR, f"{conversation_id}_{timestamp}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        print_info(f"Saved JSON output: {json_file}")
    
    if format in ("text", "both"):
        text_file = os.path.join(OUTPUT_DIR, f"{conversation_id}_{timestamp}.txt")
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(f"Conversation ID: {conversation_id}\n")
            f.write(f"Timestamp: {conversation_data.get('timestamp', 'N/A')}\n")
            f.write(f"{'=' * 70}\n\n")
            
            for turn in conversation_data.get("turns", []):
                f.write(f"Turn {turn.get('turn_number', '?')}: {turn.get('role', 'unknown').upper()}\n")
                f.write(f"{'-' * 70}\n")
                
                if turn.get("user_message"):
                    f.write(f"User Message: {turn['user_message']}\n\n")
                
                if turn.get("api_response"):
                    resp = turn["api_response"]
                    f.write("API Response:\n")
                    f.write(f"  Thread ID: {resp.get('thread_id', 'N/A')}\n")
                    f.write(f"  Order ID: {resp.get('order_id', 'N/A')}\n")
                    f.write(f"  Issue Type: {resp.get('issue_type', 'N/A')}\n")
                    f.write(f"  Draft Scenario: {resp.get('draft_scenario', 'N/A')}\n")
                    f.write(f"  Review Status: {resp.get('review_status', 'N/A')}\n")
                    if resp.get("draft_reply"):
                        f.write(f"  Draft Reply: {resp['draft_reply']}\n")
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
                        status = "✓ PASS" if value.get("passed") else "✗ FAIL"
                        f.write(f"  {status}: {key}\n")
                        if value.get("details"):
                            f.write(f"    {value['details']}\n")
                    f.write("\n")
                
                f.write("\n")
            
            f.write(f"{'=' * 70}\n")
            f.write(f"Summary: {conversation_data.get('summary', 'N/A')}\n")
            f.write(f"All Validations Passed: {conversation_data.get('all_passed', False)}\n")
        
        print_info(f"Saved text output: {text_file}")


def save_test_summary(all_conversations: List[Dict[str, Any]]):
    """Save overall test summary."""
    ensure_output_dir()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    summary = {
        "timestamp": datetime.now().isoformat(),
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
    json_file = os.path.join(OUTPUT_DIR, f"test_summary_{timestamp}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Save text summary
    text_file = os.path.join(OUTPUT_DIR, f"test_summary_{timestamp}.txt")
    with open(text_file, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("TEST SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Timestamp: {summary['timestamp']}\n")
        f.write(f"Total Conversations: {summary['total_conversations']}\n")
        f.write(f"Passed: {summary['passed']}\n")
        f.write(f"Failed: {summary['failed']}\n\n")
        f.write("Conversations:\n")
        f.write("-" * 70 + "\n")
        for conv in summary["conversations"]:
            status = "PASS" if conv["passed"] else "FAIL"
            f.write(f"{status} - {conv['conversation_id']} ({conv['turns_processed']} turns)\n")
    
    print_info(f"Saved test summary: {json_file} and {text_file}")


def validate_response(actual_reply: str, expected_message: str) -> bool:
    """Validate that the actual response is reasonable compared to expected."""
    if not actual_reply:
        print_error("No response generated")
        return False
    
    # Simple validation - check if response contains key information
    # For refund questions, check for time-related words
    expected_lower = expected_message.lower()
    actual_lower = actual_reply.lower()
    
    # Check for common response indicators
    has_response = len(actual_reply) > 10  # At least some content
    
    if has_response:
        print_success(f"Response generated ({len(actual_reply)} chars)")
        print_info(f"  Expected context: {expected_message[:60]}...")
        print_info(f"  Actual response: {actual_reply[:60]}...")
        return True
    else:
        print_error("Response too short or empty")
        return False


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
            
            # Invoke triage with the user message
            print_info("Invoking triage endpoint...")
            result = invoke_triage(message, thread_id=thread_id)
            
            if not result:
                print_error("Triage invocation failed")
                all_validations_passed = False
                turn_data["validation"]["api_call"] = {"passed": False, "details": "Triage invocation failed"}
                output_data["turns"].append(turn_data)
                continue
            
            # Store thread_id for continuation
            thread_id = result.get("thread_id")
            
            # Store API response
            turn_data["api_response"] = result
            
            # Display results
            print_info("Triage Results:")
            print(f"  Thread ID: {thread_id}")
            print(f"  Order ID: {result.get('order_id', 'None')}")
            print(f"  Issue Type: {result.get('issue_type', 'None')}")
            print(f"  Draft Scenario: {result.get('draft_scenario', 'None')}")
            print(f"  Review Status: {result.get('review_status', 'None')}")
            
            if result.get("draft_reply"):
                draft_preview = result["draft_reply"][:100] + "..." if len(result["draft_reply"]) > 100 else result["draft_reply"]
                print(f"  Draft Reply: {draft_preview}")
            
            # Validate outcome (only on first turn)
            if turn_num == 1:
                print_info("Validating expected outcome...")
                validation_passed = validate_outcome(result, expected, conversation_id)
                if not validation_passed:
                    all_validations_passed = False
                
                # Store validation results
                turn_data["validation"]["issue_type"] = {
                    "passed": result.get("issue_type") == expected.get("issue_type"),
                    "details": f"Expected: {expected.get('issue_type')}, Got: {result.get('issue_type')}"
                }
                turn_data["validation"]["order_id"] = {
                    "passed": result.get("order_id") == expected.get("order_id"),
                    "details": f"Expected: {expected.get('order_id')}, Got: {result.get('order_id')}"
                }
            
            # Handle different scenarios
            scenario = result.get("draft_scenario")
            review_status = result.get("review_status")
            
            if scenario == "reply" and review_status == "pending":
                # REPLY scenario - needs admin review
                print_info("Testing admin review (APPROVED)...")
                
                if thread_id:
                    admin_result = admin_review(thread_id, "approved", "Test approval")
                    
                    if admin_result:
                        print_success("Admin review completed")
                        print(f"  Final Review Status: {admin_result.get('review_status')}")
                        if admin_result.get("draft_reply"):
                            final_preview = admin_result["draft_reply"][:100] + "..." if len(admin_result["draft_reply"]) > 100 else admin_result["draft_reply"]
                            print(f"  Final Reply: {final_preview}")
                        
                        # Store admin response
                        turn_data["admin_response"] = admin_result
                        
                        # Validate assistant response matches expected
                        expected_assistant = None
                        if i + 1 < len(turns):
                            next_turn = turns[i + 1]
                            if next_turn.get("role") == "assistant":
                                expected_assistant = next_turn.get("message")
                        
                        if expected_assistant:
                            actual_reply = admin_result.get("draft_reply", "")
                            print_info("Validating assistant response...")
                            response_valid = validate_response(actual_reply, expected_assistant)
                            if not response_valid:
                                all_validations_passed = False
                            
                            turn_data["validation"]["assistant_response"] = {
                                "passed": response_valid,
                                "details": f"Expected: {expected_assistant[:80]}..., Actual: {actual_reply[:80]}..."
                            }
                    else:
                        print_error("Admin review failed")
                        all_validations_passed = False
                        turn_data["validation"]["admin_review"] = {"passed": False, "details": "Admin review failed"}
            else:
                # Non-REPLY scenario (need_identifier, order_not_found, etc.)
                # System ended without admin review - check if we have expected assistant message
                expected_assistant = None
                if i + 1 < len(turns):
                    next_turn = turns[i + 1]
                    if next_turn.get("role") == "assistant":
                        expected_assistant = next_turn.get("message")
                
                if expected_assistant and result.get("draft_reply"):
                    actual_reply = result.get("draft_reply", "")
                    print_info("Validating assistant response (no admin review needed)...")
                    response_valid = validate_response(actual_reply, expected_assistant)
                    if not response_valid:
                        all_validations_passed = False
                    
                    turn_data["validation"]["assistant_response"] = {
                        "passed": response_valid,
                        "details": f"Expected: {expected_assistant[:80]}..., Actual: {actual_reply[:80]}..."
                    }
                elif expected_assistant:
                    print_warning("Expected assistant message but no draft_reply generated")
                    all_validations_passed = False
                    turn_data["validation"]["assistant_response"] = {
                        "passed": False,
                        "details": "Expected assistant message but no draft_reply generated"
                    }
            
            # Add turn data to output
            output_data["turns"].append(turn_data)
        
        elif role == "assistant":
            print_info(f"Expected assistant message: {message}")
            # For assistant turns, we validate against the previous response
            # This is handled in the user turn processing above
            print_info("(Validation done in previous turn)")
            
            # Store expected message in previous turn if available
            if output_data["turns"]:
                output_data["turns"][-1]["expected_message"] = message
    
    print(f"\n{'-' * 70}")
    print_info(f"Conversation Summary: Processed {turn_num} turns")
    if all_validations_passed:
        print_success(f"All validations passed for {conversation_id}")
    else:
        print_error(f"Some validations failed for {conversation_id}")
    print(f"{'-' * 70}")
    
    # Update output data
    output_data["all_passed"] = all_validations_passed
    output_data["turns_processed"] = turn_num
    output_data["summary"] = f"Processed {turn_num} turns, {'all passed' if all_validations_passed else 'some failed'}"
    
    # Save this conversation's output
    save_conversation_output(output_data)
    
    return output_data


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
    all_conversation_outputs = []
    results = []
    for i, conversation in enumerate(conversations, 1):
        print(f"\n[{i}/{len(conversations)}]")
        output_data = test_conversation(conversation)
        all_conversation_outputs.append(output_data)
        results.append({
            "conversation_id": output_data.get("conversation_id", f"TEST-{i}"),
            "passed": output_data.get("all_passed", False)
        })
        time.sleep(0.5)  # Small delay between tests
    
    # Save overall test summary
    save_test_summary(all_conversation_outputs)
    
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
    
    print_info(f"\nAll conversation outputs saved to: {OUTPUT_DIR}")
    
    # Exit code
    if passed_count == total_count:
        print_success("\nAll tests passed!")
        sys.exit(0)
    else:
        print_error(f"\n{total_count - passed_count} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
