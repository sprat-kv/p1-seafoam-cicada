# Test Script Update - Multi-Turn Conversation Support

## What Changed

The `test_e2e.py` script has been updated to process **all turns** in each conversation, not just the first message.

## New Features

### 1. **Multi-Turn Processing**
- Processes all user and assistant turns in sequence
- Maintains conversation context using `thread_id`
- Validates responses at each turn

### 2. **Enhanced Validation**
- Validates expected outcomes on first turn (issue_type, order_id)
- Validates assistant responses match expected messages
- Checks response quality (length, content)

### 3. **Better Output**
- Shows each turn with clear separators
- Displays conversation summary at the end
- Color-coded validation results

## How It Works

### Example: P1-DEMO-001

**Turn 1: User**
```
"I'd like a refund for order ORD1001. The mouse is not working."
```
- System processes ticket
- Extracts order_id: ORD1001
- Classifies: refund_request
- Fetches order details
- Generates draft reply
- Goes to admin review
- Admin approves
- Validates response matches expected

**Turn 2: Assistant (Expected)**
```
"We identified a refund request for order ORD1001. Reviewing details..."
```
- Validates actual response contains similar information

**Turn 3: User**
```
"When will I get the refund?"
```
- System processes follow-up question
- Uses same thread_id to continue conversation
- Generates response

**Turn 4: Assistant (Expected)**
```
"Refund will be issued within 5 business days."
```
- Validates response matches expected

## Running the Tests

```bash
# Make sure API server is running
uv run uvicorn app.main:app --reload

# In another terminal, run tests
uv run python test_e2e.py
```

## Output Format

```
======================================================================
Testing Conversation: P1-DEMO-001
======================================================================

----------------------------------------------------------------------
Turn 1: USER
----------------------------------------------------------------------
ℹ User message: I'd like a refund for order ORD1001...
ℹ Invoking triage endpoint...
ℹ Triage Results:
  Thread ID: abc-123-def
  Order ID: ORD1001
  Issue Type: refund_request
  Draft Scenario: reply
  Review Status: pending
  Draft Reply: Hi Ava Chen, we are sorry...
✓ Issue type: refund_request
✓ Order ID: ORD1001
ℹ Testing admin review (APPROVED)...
✓ Admin review completed
✓ Response generated (120 chars)

----------------------------------------------------------------------
Turn 2: ASSISTANT
----------------------------------------------------------------------
ℹ Expected assistant message: We identified a refund request...
ℹ (Validation done in previous turn)

----------------------------------------------------------------------
Turn 3: USER
----------------------------------------------------------------------
ℹ User message: When will I get the refund?
...

----------------------------------------------------------------------
Turn 4: ASSISTANT
----------------------------------------------------------------------
...

----------------------------------------------------------------------
ℹ Conversation Summary: Processed 4 turns
✓ All validations passed for P1-DEMO-001
----------------------------------------------------------------------
```

## Important Notes

1. **Follow-up Questions**: The system processes follow-up questions as new ticket triage requests. This is by design - each user message triggers a new triage flow.

2. **Thread Continuity**: The `thread_id` is maintained across turns, but each turn is processed independently.

3. **Response Validation**: The validation checks that responses are generated and contain reasonable content, but doesn't do exact text matching (since LLM responses vary).

4. **Admin Review**: Only REPLY scenarios go through admin review. Other scenarios (need_identifier, order_not_found, etc.) return directly to the user.

## Future Enhancements

- Add semantic similarity checking for responses
- Support for conversation context awareness
- Better handling of follow-up questions
- Response quality scoring
